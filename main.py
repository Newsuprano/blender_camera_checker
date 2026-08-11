import sys
from pathlib import Path
import subprocess

import pandas as pd

from PyQt6.QtCore import (
    QThread, 
    pyqtSignal, 
    Qt,
    QTimeLine,
    QSize,
    QTimer
)

from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton, 
    QTableView, 
    QHeaderView, 
    QDialog, 
    QLabel, 
    QFileDialog, 
    QMessageBox,
    QToolBar,
    QInputDialog,
    QProgressBar,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QToolButton,
    QMenu,
    QStyle,
    QSizePolicy
)
from PyQt6.QtGui import (
    QAction,
    QIcon,
    QTransform
)

from cache import load_cache, save_cache
from frame_details_dialog import FrameDetailsDialog
from logic import (
    count_frame_statuses, 
    create_mismatched_dataframe, 
    load_and_pivot_data
)
from script import run_batch_extraction
from settings_dialog import SettingsDialog
from ui_table_model import CameraTableModel

ARROW_ICON_PATH = Path(__file__).parent / "assets" / "icons" / "arrow.png"
RUN_ICON_PATH = Path(__file__).parent / "assets" / "icons" / "play_arrow.png"
OPEN_ICON_PATH = Path(__file__).parent / "assets" / "icons" / "history.png"
SETTINGS_ICON_PATH = Path(__file__).parent / "assets" / "icons" / "settings.png"

class MainWindow(QMainWindow) :
    def __init__(self) :
        super().__init__()
        self.setWindowTitle("Camera Sync Checker")
        self.resize(900, 600)

        cache = load_cache()
        self.blender_exe_path = cache.get("blender_exe_path", r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
        self.last_input_dir = cache.get("last_input_dir", "")
        self.last_output_dir = cache.get("last_output_dir", "")

        self.current_csv_path = Path("output/camera_data.csv")
        self.output_filename = "camera_data.csv"

        self.is_extracting = False

        # Load initial data safely
        try:
            self.pivot_df = load_and_pivot_data(str(self.current_csv_path))
            identical_count, mismatched_count, bad_frames = count_frame_statuses(self.pivot_df)
            self.mismatched_df = create_mismatched_dataframe(self.pivot_df, bad_frames)
        except Exception:
            self.pivot_df = pd.DataFrame()
            self.mismatched_df = pd.DataFrame()
            identical_count, mismatched_count = 0, 0

        total_frames = len(self.pivot_df.columns) if not self.pivot_df.empty else 0
        matching_percentage = (identical_count / total_frames * 100) if total_frames > 0 else 0

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- TOOLBAR SETUP ---
        self.toolbar = QToolBar("Main Toolbar")

        self.toolbar.setIconSize(QSize(22, 22))

        self.toolbar.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px 6px;
                margin: 2px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 35);
                border-radius: 4px;
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 55);
            }
        """)
        
        cache = load_cache()
        saved_area = cache.get("toolbar_area", None)
        
        if saved_area is not None:
            self.addToolBar(Qt.ToolBarArea(saved_area), self.toolbar)
        else:
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.toolbar.allowedAreasChanged.connect(self.save_toolbar_state)
        self.toolbar.allowedAreasChanged.connect(self.deferred_update_toolbar_display_mode)
        self.toolbar.topLevelChanged.connect(self.save_toolbar_state)
        self.toolbar.topLevelChanged.connect(self.deferred_update_toolbar_display_mode)

        style = self.style()

        # 1. Run New Pipeline Action (e.g., 14x14)
        run_icon = self.create_custom_sized_icon(RUN_ICON_PATH, 24, 24) if RUN_ICON_PATH.exists() else style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.run_pipeline_action = self.toolbar.addAction(run_icon, "Run New Pipeline")
        self.run_pipeline_action.triggered.connect(self.on_run_new_pipeline)

        self.toolbar.addSeparator()

        # 2. Use Existing Pipeline Action (e.g., 16x16)
        open_icon = self.create_custom_sized_icon(OPEN_ICON_PATH, 16, 16) if OPEN_ICON_PATH.exists() else style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)
        self.open_existing_action = self.toolbar.addAction(open_icon, "Use Existing Pipeline")
        self.open_existing_action.triggered.connect(self.on_open_existing_pipeline)

        self.toolbar.addSeparator()

        # 3. Settings Action (e.g., 18x18)
        settings_icon = self.create_custom_sized_icon(SETTINGS_ICON_PATH, 18, 18) if SETTINGS_ICON_PATH.exists() else style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.settings_action = self.toolbar.addAction(settings_icon, "Settings")
        self.settings_action.triggered.connect(self.on_open_settings)

        self.toolbar.addSeparator()

        # 4. Mismatch Checkbox
        self.mismatch_checkbox = QCheckBox("Show Mismatches Only")
        self.mismatch_checkbox.toggled.connect(self.on_toggle_mismatches_checkbox)
        self.toolbar.addWidget(self.mismatch_checkbox)

        # 5. Expanding Spacer (Pushes the dropdown button to the far right/bottom)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.toolbar.addWidget(spacer)

        # 6. Dropdown Menu Button with Smooth Rotating Arrow Animation
        self.display_menu_btn = QToolButton(self.toolbar)
        self.display_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.display_menu_btn.setStyleSheet("""
            QToolButton::menu-indicator { image: none; }
            QToolButton { background: transparent; border: none; padding: 4px; }
            QToolButton:hover { background: rgba(255, 255, 255, 30); border-radius: 4px; }
        """)

        menu = QMenu(self.display_menu_btn)
        
        self.action_toggle_icons = QAction("Display Icons", self, checkable=True)
        self.action_toggle_icons.setChecked(True)
        self.action_toggle_icons.triggered.connect(self.update_toolbar_display_mode)
        self.action_toggle_icons.triggered.connect(self.save_toolbar_state)
        menu.addAction(self.action_toggle_icons)

        self.action_toggle_text = QAction("Display Text", self, checkable=True)
        self.action_toggle_text.setChecked(True)
        self.action_toggle_text.triggered.connect(self.update_toolbar_display_mode)
        self.action_toggle_text.triggered.connect(self.save_toolbar_state)
        menu.addAction(self.action_toggle_text)

        self.display_menu_btn.setMenu(menu)

        # Helper to compute angles based on docking area and trigger the animation
        def trigger_smooth_rotation(is_open):
            area = self.toolBarArea(self.toolbar)
            angles = {
                Qt.ToolBarArea.TopToolBarArea: (0, 180),
                Qt.ToolBarArea.BottomToolBarArea: (180, 0),
                Qt.ToolBarArea.LeftToolBarArea: (270, 90),
                Qt.ToolBarArea.RightToolBarArea: (90, 270)
            }
            default_angle, flipped_angle = angles.get(area, (0, 180))
            
            if is_open:
                self.animate_arrow_rotation(default_angle, flipped_angle)
            else:
                self.animate_arrow_rotation(flipped_angle, default_angle)

        # Initial setup on startup (snaps to resting position instantly)
        self.update_arrow_icon(is_open=False)

        # Connect signals to trigger smooth rotation when opening and closing
        menu.aboutToShow.connect(lambda: trigger_smooth_rotation(is_open=True))
        menu.aboutToHide.connect(lambda: trigger_smooth_rotation(is_open=False))

        self.toolbar.addWidget(self.display_menu_btn)
        
        self.action_toggle_icons.setChecked(cache.get("icons_visible", True))
        self.action_toggle_text.setChecked(cache.get("text_visible", True))

        self.update_toolbar_display_mode()
        self.update_arrow_to_resting_state()
        # ---------------------

        # Main Table View
        self.table_view = QTableView()
        self.model = CameraTableModel(self.pivot_df)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        # Setup vertical header clicking for opening blend files
        vertical_header = self.table_view.verticalHeader()
        vertical_header.setSectionsClickable(True)
        vertical_header.sectionDoubleClicked.connect(self.on_camera_row_header_clicked)

        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setSectionsClickable(True)
        horizontal_header.sectionClicked.connect(self.on_frame_header_clicked)

        # --- INFO PANEL SETUP ---
        self.info_panel_widget = QWidget()
        info_layout = QHBoxLayout(self.info_panel_widget)
        info_layout.setContentsMargins(10, 5, 10, 5)

        self.match_label = QLabel(f"<b>Matching Frames:</b> {identical_count}")
        self.mismatch_label = QLabel(f"<b>Mismatched Frames:</b> {mismatched_count}")
        self.percent_label = QLabel(f"<b>Sync Rate:</b> {matching_percentage:.1f}%")

        info_layout.addWidget(self.match_label)
        info_layout.addWidget(self.mismatch_label)
        info_layout.addStretch()
        info_layout.addWidget(self.percent_label)

        # Added to the correct main layout variable
        layout.addWidget(self.info_panel_widget)

    def deferred_update_toolbar_display_mode(self, *args):
        # Wait 10ms for Qt to finish docking the toolbar before checking dimensions
        QTimer.singleShot(10, self.update_toolbar_display_mode)

    def update_arrow_to_resting_state(self):
        area = self.toolBarArea(self.toolbar)
        angles = {
            Qt.ToolBarArea.TopToolBarArea: 0,      # Points down
            Qt.ToolBarArea.BottomToolBarArea: 180, # Points up
            Qt.ToolBarArea.LeftToolBarArea: 270,   # Inverted: points right from the left edge
            Qt.ToolBarArea.RightToolBarArea: 90    # Inverted: points left from the right edge
        }
        resting_angle = angles.get(area, 0)
        self.display_menu_btn.setIcon(self.create_rotated_icon(ARROW_ICON_PATH, resting_angle, 14, 14))

    def on_camera_row_header_clicked(self, logical_index):
        self.close_active_frame_dialog()
        
        camera_name = self.model.headerData(logical_index, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole)
        
        cache = load_cache()
        input_dir = self.last_input_dir if hasattr(self, "last_input_dir") and self.last_input_dir else cache.get("last_input_dir", "")
        
        if input_dir:
            input_path = Path(input_dir)
            blend_file = input_path / f"{camera_name}.blend"
            
            if not blend_file.exists():
                matching_files = list(input_path.glob(f"*{camera_name}*.blend"))
                if matching_files:
                    blend_file = matching_files[0]

            if blend_file.exists():
                try:
                    subprocess.Popen([self.blender_exe_path, str(blend_file)])
                except Exception as e:
                    QMessageBox.critical(self, "Launch Error", f"Could not launch Blender:\n{str(e)}")
            else:
                QMessageBox.warning(self, "File Not Found", f"Could not find a .blend file for '{camera_name}' in:\n{input_path}")
        else:
            QMessageBox.warning(self, "Input Folder Needed", "Please run the pipeline or use an existing pipeline first so the app knows where the source .blend files are located.")

    def create_custom_sized_icon(self, icon_path, width, height):
        base_icon = QIcon(str(icon_path))
        # Scale the pixmap directly to your custom dimensions
        pixmap = base_icon.pixmap(width, height)
        return QIcon(pixmap)

    def animate_arrow_rotation(self, start_angle, end_angle):
        # Stop and clean up any existing timeline animation
        if hasattr(self, "_arrow_timeline") and self._arrow_timeline.state() == QTimeLine.State.Running:
            self._arrow_timeline.stop()

        # Create a 150ms timeline with 30 frames
        self._arrow_timeline = QTimeLine(150, self)
        self._arrow_timeline.setFrameRange(0, 30)
        
        # Connect the frame updates to calculate angle interpolation smoothly
        self._arrow_timeline.frameChanged.connect(lambda frame: self.update_interpolated_icon(start_angle, end_angle, frame, 30))
        
        self._arrow_timeline.start()

    def update_interpolated_icon(self, start_angle, end_angle, frame, max_frames):
        # Linear interpolation (lerp) from start to end angle based on current frame
        progress = frame / float(max_frames)
        current_angle = start_angle + (end_angle - start_angle) * progress
        self.display_menu_btn.setIcon(self.create_rotated_icon(ARROW_ICON_PATH, current_angle))

    def update_arrow_icon(self, is_open=False):
        # Find out which area the toolbar is currently docked in
        area = self.toolBarArea(self.toolbar)
            
        angles = {
            Qt.ToolBarArea.TopToolBarArea: (0, 180),       # Default Down, Clicked Up
            Qt.ToolBarArea.BottomToolBarArea: (180, 0),    # Default Up, Clicked Down
            Qt.ToolBarArea.LeftToolBarArea: (90, 270),     # Flipped: Points inward from the left
            Qt.ToolBarArea.RightToolBarArea: (270, 90)     # Flipped: Points inward from the right
        }
            
        default_angle, flipped_angle = angles.get(area, (0, 180))
        target_angle = flipped_angle if is_open else default_angle
            
        # Always apply the rotated icon directly
        self.display_menu_btn.setIcon(self.create_rotated_icon(ARROW_ICON_PATH, target_angle))

    def create_rotated_icon(self, icon_path, angle_degrees, width=24, height=24):
        base_icon = QIcon(str(icon_path))
        pixmap = base_icon.pixmap(width, height)
        transform = QTransform().rotate(angle_degrees)
        rotated_pixmap = pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        return QIcon(rotated_pixmap)

    def update_toolbar_display_mode(self):
        icons_checked = self.action_toggle_icons.isChecked()
        text_checked = self.action_toggle_text.isChecked()

        # Enforce rule: at least one must be checked
        if not icons_checked and not text_checked:
            sender = self.sender()
            if sender:
                sender.setChecked(True)
            return

        # Set the tool button style based on user preference
        if icons_checked and text_checked:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        elif icons_checked and not text_checked:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        elif not icons_checked and text_checked:
            self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        # Check if the toolbar is currently docked vertically (Left or Right)
        area = self.toolBarArea(self.toolbar)
        is_vertical = area in (Qt.ToolBarArea.LeftToolBarArea, Qt.ToolBarArea.RightToolBarArea)

        if is_vertical and not text_checked:
            # Constrict width for vertical icon-only mode
            self.toolbar.setMaximumWidth(45)
            self.toolbar.setMinimumWidth(35)
            self.toolbar.setMaximumHeight(16777215) # Free height constraint
            self.toolbar.setMinimumHeight(0)
            
            if hasattr(self, "mismatch_checkbox"):
                self.mismatch_checkbox.setText("")
                self.mismatch_checkbox.setToolTip("Show Mismatches Only")
                self.mismatch_checkbox.setStyleSheet("""
                    QCheckBox {
                        margin-left: 12px; 
                        margin-top: 6px;
                        spacing: 2px;
                    }
                    QCheckBox::indicator {
                        width: 18px;
                        height: 18px;
                    }
                """)
        else:
            # Free up width and height constraints when horizontal or showing text
            self.toolbar.setMaximumWidth(16777215)
            self.toolbar.setMinimumWidth(0)
            self.toolbar.setMaximumHeight(16777215)
            self.toolbar.setMinimumHeight(0)
            
            if hasattr(self, "mismatch_checkbox"):
                self.mismatch_checkbox.setText("Show Mismatches Only")
                self.mismatch_checkbox.setToolTip("")
                self.mismatch_checkbox.setStyleSheet("")

            self.toolbar.adjustSize()
            self.toolbar.updateGeometry()
    
    def on_open_settings(self) :
        dialog = SettingsDialog(self.blender_exe_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.blender_path:
                self.blender_exe_path = dialog.blender_path
                save_cache({"blender_exe_path": self.blender_exe_path})
                QMessageBox.information(self, "Success", "Settings saved successfully.")

    def close_active_frame_dialog(self):
        if hasattr(self, "active_frame_dialog") and self.active_frame_dialog is not None:
            self.active_frame_dialog.close()
            self.active_frame_dialog = None

    def on_frame_header_clicked(self, logical_index) :
        self.close_active_frame_dialog()
        frame_name = self.model._df.columns[logical_index]
        column_data = self.model._df[frame_name]

        self.active_frame_dialog = FrameDetailsDialog(frame_name, column_data, self)
        self.active_frame_dialog.show()

    def on_toggle_mismatches_checkbox(self, checked) :
        if checked :
            self.model.update_data(self.mismatched_df)
        else :
            self.model.update_data(self.pivot_df)
 
    def on_run_new_pipeline(self) :
        dialog = PipelineConfigDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        input_dir = dialog.input_dir
        output_dir = dialog.output_dir

        if not input_dir or not output_dir:
            return

        self.last_input_dir = input_dir
        self.last_output_dir = output_dir
        save_cache({
            "last_input_dir" : self.last_input_dir,
            "last_output_dir" : self.last_output_dir 
        })

        custom_name, ok = QInputDialog.getText(
            self, "CSV Filename", "Enter name for the output CSV file", text="camera_data.csv"
        )
        if not ok or not custom_name.strip() :
            return

        if not custom_name.endswith(".csv") :
            custom_name += ".csv"

        self.output_filename = custom_name.strip()
        target_csv_path = Path(output_dir) / self.output_filename

        if target_csv_path.exists():
            reply = QMessageBox.warning(
                self,
                "File Already Exists",
                f"The file '{self.output_filename}' already exists in the selected output folder.\n\n"
                "Running the pipeline will replace the existing file.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return

        progress_dialog = ProgressDialog(input_dir, output_dir, self.blender_exe_path, self)
        result_code = progress_dialog.exec()

        if result_code == QDialog.DialogCode.Accepted:
            try:
                default_generated_path = Path(output_dir) / "camera_data.csv"
                self.current_csv_path = target_csv_path
                
                if default_generated_path.exists() and default_generated_path != self.current_csv_path:
                    if self.current_csv_path.exists():
                        self.current_csv_path.unlink()
                    default_generated_path.rename(self.current_csv_path)

                self.load_data_into_app(str(self.current_csv_path))
                save_cache({"last_csv_path": str(self.current_csv_path)})
                QMessageBox.information(self, "Success", f"Pipeline executed successfully!\nSaved as: {self.output_filename}")
            except Exception as e :
                QMessageBox.critical(self, "Pipeline Error", f"An error occurred while saving/loading:\n{str(e)}")
        else:
            if progress_dialog.error_message:
                QMessageBox.critical(self, "Pipeline Error", f"An error occurred during execution:\n{progress_dialog.error_message}")

    def on_open_existing_pipeline(self):
        cache = load_cache()
        # Get the last used file path from cache, falling back to an empty string
        default_file = cache.get("last_csv_path", "")

        dialog = ExistingPipelineDialog(default_file, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        file_path = dialog.selected_file
        if not file_path:
            return

        try:
            self.current_csv_path = Path(file_path)
            # Save the full file path to the cache
            save_cache({"last_csv_path": str(self.current_csv_path)})

            self.load_data_into_app(str(self.current_csv_path))
            QMessageBox.information(self, "Loaded", f"Successfully loaded report:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Could not parse the selected file:\n{str(e)}")

    def load_data_into_app(self, csv_path) :
        self.pivot_df = load_and_pivot_data(csv_path)
        _, _, bad_frames = count_frame_statuses(self.pivot_df)
        self.mismatched_df = create_mismatched_dataframe(self.pivot_df, bad_frames)

        if self.mismatch_checkbox.isChecked() :
            self.model.update_data(self.mismatched_df)
        else :
            self.model.update_data(self.pivot_df)
            
        self.update_info_panel(self.pivot_df)

    def update_info_panel(self, df):
        total_frames = len(df.columns) if not df.empty else 0
        identical_count, mismatched_count, _ = count_frame_statuses(df) if not df.empty else (0, 0, [])
        matching_percentage = (identical_count / total_frames * 100) if total_frames > 0 else 0

        self.match_label.setText(f"<b>Matching Frames:</b> {identical_count}")
        self.mismatch_label.setText(f"<b>Mismatched Frames:</b> {mismatched_count}")
        self.percent_label.setText(f"<b>Sync Rate:</b> {matching_percentage:.1f}%")

    def closeEvent(self, event):
        """Intercepts the close event to prevent exiting during data extraction."""
        if hasattr(self, "is_extracting") and self.is_extracting:
            # Prompt the user that extraction is still in progress
            reply = QMessageBox.warning(
                self,
                "Extraction in Progress",
                "Blender data extraction is currently running.\nAre you sure you want to quit? This may corrupt temporary files.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()  # Let the app close
            else:
                event.ignore()  # Cancel the close event
        else:
            event.accept()  # Safe to close normally

    def save_toolbar_state(self):
        cache = load_cache()
        
        area = self.toolBarArea(self.toolbar)
        cache["toolbar_area"] = int(area.value) if hasattr(area, "value") else int(area)
        
        # ---> ADD THESE TWO LINES TO SAVE DISPLAY STATES <---
        cache["icons_visible"] = self.action_toggle_icons.isChecked()
        cache["text_visible"] = self.action_toggle_text.isChecked()
        
        save_cache(cache)
        self.update_arrow_to_resting_state()

class PipelineConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Run Pipeline Configuration")
        self.resize(520, 240)

        self.input_dir = ""
        self.output_dir = ""

        layout = QVBoxLayout(self)

        # Input Folder Section
        layout.addWidget(QLabel("<b>Input Folder :</b>"))
        input_layout = QHBoxLayout()
        self.input_input = QLineEdit()
        self.input_input.setPlaceholderText("Select or type input folder path...")
        self.input_input.textChanged.connect(self.check_ready)
        
        input_btn = QPushButton("Select Input Folder")
        input_btn.clicked.connect(self.select_input_folder)
        
        input_layout.addWidget(self.input_input, stretch=1)
        input_layout.addWidget(input_btn)
        layout.addLayout(input_layout)

        layout.addSpacing(10)

        # Output Folder Section
        layout.addWidget(QLabel("<b>Output Folder :</b>"))
        output_layout = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("Select or type output folder path...")
        self.output_input.textChanged.connect(self.check_ready)
        
        output_btn = QPushButton("Select Output Folder")
        output_btn.clicked.connect(self.select_output_folder)
        
        output_layout.addWidget(self.output_input, stretch=1)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)

        layout.addSpacing(15)

        # Run Action Button
        self.run_btn = QPushButton("Run Pipeline")
        self.run_btn.setEnabled(False)
        self.run_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.run_btn.clicked.connect(self.on_run_clicked)
        layout.addWidget(self.run_btn)

    def select_input_folder(self):
        current_text = self.input_input.text().strip()
        start_dir = current_text if current_text and Path(current_text).exists() else ""
        
        dir_path = QFileDialog.getExistingDirectory(self, "Select Input Folder with .blend files", start_dir)
        if dir_path:
            self.input_input.setText(dir_path)

    def select_output_folder(self):
        current_text = self.output_input.text().strip()
        start_dir = current_text if current_text and Path(current_text).exists() else ""
        
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Destination Folder", start_dir)
        if dir_path:
            self.output_input.setText(dir_path)

    def check_ready(self):
        # Enable Run Pipeline button only when both fields have text
        in_text = self.input_input.text().strip()
        out_text = self.output_input.text().strip()
        
        if in_text and out_text:
            self.run_btn.setEnabled(True)
        else:
            self.run_btn.setEnabled(False)

    def on_run_clicked(self):
        # Capture final values from text inputs before accepting
        self.input_dir = self.input_input.text().strip()
        self.output_dir = self.output_input.text().strip()
        self.accept()

class PipelineWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, input_dir, output_dir, blender_exe_path):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.blender_exe_path = blender_exe_path

    def run(self):
        try:
            self.progress_updated.emit(10, "Initializing Blender batch process...")
            self.is_extracting = True
            self.progress_updated.emit(40, "Running extraction script on blend files...")
            run_batch_extraction(self.input_dir, self.output_dir, self.blender_exe_path)
            
            self.progress_updated.emit(90, "Finalizing report generation...")
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class ProgressDialog(QDialog):
    def __init__(self, input_dir, output_dir, blender_exe_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Running Pipeline...")
        self.resize(450, 160)
        self.setModal(True)
        
        # Track extraction state immediately
        self.is_extracting = True
        self.error_message = ""

        # Remove the close button ('X') from the title bar
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        layout = QVBoxLayout(self)

        self.status_label = QLabel("Preparing execution...")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(10)

        # Start background worker thread
        self.worker = PipelineWorker(input_dir, output_dir, blender_exe_path)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def on_finished(self, success, err_str):
        self.is_extracting = False
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Pipeline completed successfully!")
            self.accept()
        else:
            self.error_message = err_str
            self.reject()

    def keyPressEvent(self, event):
        """Prevents pressing the Escape key from closing the dialog."""
        if event.key() == Qt.Key.Key_Escape and self.is_extracting:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Prevents Alt+F4 or system close commands while extracting."""
        if self.is_extracting:
            event.ignore()
        else:
            event.accept()

class ExistingPipelineDialog(QDialog):
    def __init__(self, default_path="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Use Existing Pipeline Report")
        self.resize(500, 150)

        layout = QVBoxLayout(self)

        # Instruction label
        layout.addWidget(QLabel("Select an existing CSV pipeline report:"))

        # Path selection layout
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit(default_path)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        # Dialog buttons (OK / Cancel)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Existing Pipeline Report", self.path_input.text(), "CSV Files (*.csv)"
        )
        if file_path:
            self.path_input.setText(file_path)

    @property
    def selected_file(self):
        return self.path_input.text()




if __name__ == "__main__" :
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())