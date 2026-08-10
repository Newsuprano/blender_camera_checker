import sys
from pathlib import Path
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
    QTableWidget, 
    QTableWidgetItem, 
    QFileDialog, 
    QMessageBox,
    QToolBar,
    QInputDialog,
    QProgressBar,
    QLineEdit,
    QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QColor, QBrush, QIcon
from logic import load_and_pivot_data, count_frame_statuses, create_mismatched_dataframe, get_frame_clusters_tuple
from ui_table_model import CameraTableModel
from script import run_batch_extraction
import subprocess
import json

CONFIG_FILE = Path("config_cache.json")

def load_cache():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(data):
    try:
        current_data = load_cache()
        current_data.update(data)
        with open(CONFIG_FILE, "w") as f:
            json.dump(current_data, f, indent=4)
    except Exception as e:
        print(f"Could not save cache: {e}")

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
        self.blender_exe_path = r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'

        # Load initial data safely
        try:
            self.pivot_df = load_and_pivot_data(str(self.current_csv_path))
            _, _, bad_frames = count_frame_statuses(self.pivot_df)
            self.mismatched_df = create_mismatched_dataframe(self.pivot_df, bad_frames)
        except Exception:
            import pandas as pd
            self.pivot_df = pd.DataFrame()
            self.mismatched_df = pd.DataFrame()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- TOOLBAR SETUP ---
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        self.run_pipeline_action = toolbar.addAction("Run New Pipeline")
        self.run_pipeline_action.triggered.connect(self.on_run_new_pipeline)

        toolbar.addSeparator()

        self.open_existing_action = toolbar.addAction("Use Existing Pipeline")
        self.open_existing_action.triggered.connect(self.on_open_existing_pipeline)

        toolbar.addSeparator()

        self.settings_action = toolbar.addAction("Settings")
        self.settings_action.triggered.connect(self.on_open_settings)

        toolbar.addSeparator()

        # Checkbox widget wrapper for the toolbar
        self.mismatch_checkbox = QCheckBox("Show Mismatches Only")
        self.mismatch_checkbox.toggled.connect(self.on_toggle_mismatches_checkbox)
        toolbar.addWidget(self.mismatch_checkbox)
        # ---------------------

        # Main Table View
        self.table_view = QTableView()
        self.model = CameraTableModel(self.pivot_df)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        # Setup vertical header clicking for opening blend files
        vertical_header = self.table_view.verticalHeader()
        vertical_header.setSectionsClickable(True)
        vertical_header.sectionClicked.connect(self.on_camera_row_header_clicked)

        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setSectionsClickable(True)
        horizontal_header.sectionClicked.connect(self.on_frame_header_clicked)

    def on_camera_row_header_clicked(self, logical_index):
        self.close_active_frame_dialog()
        
        # Get camera name from model
        camera_name = self.model.headerData(logical_index, Qt.Orientation.Vertical, Qt.ItemDataRole.DisplayRole)
        
        # Always check/reload from cache to ensure we have the latest path stored
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

    def on_open_settings(self) :
        dialog = SettingsDialog(self.blender_exe_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.blender_path:
                self.blender_exe_path = dialog.blender_path
                save_cache({"blender_exe_path": self.blender_exe_path})
                QMessageBox.information(self, "Settings Saved", f"Blender path updated to:\n{self.blender_exe_path}")

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

        # <--- ADD THIS LINE HERE so the app remembers the folder path --->
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

        # Check if file already exists and warn the user
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

        # Launch the progress popup dialog with background worker thread
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

                # Reload table data
                self.load_data_into_app(str(self.current_csv_path))
                QMessageBox.information(self, "Success", f"Pipeline executed successfully!\nSaved as: {self.output_filename}")
            except Exception as e :
                QMessageBox.critical(self, "Pipeline Error", f"An error occurred while saving/loading:\n{str(e)}")
        else:
            if progress_dialog.error_message:
                QMessageBox.critical(self, "Pipeline Error", f"An error occurred during execution:\n{progress_dialog.error_message}")

    def on_open_existing_pipeline(self) :
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Existing Pipeline Report", "", "CSV Files (*.csv)"
        )
        if not file_path :
            return

        try:
            self.current_csv_path = Path(file_path)
            self.last_output_dir = str(self.current_csv_path.parent)
            save_cache({"last_output_dir" : self.last_output_dir})

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
            # If your run_batch_extraction script supports progress callbacks, you can hook them here.
            # Running standard extraction:
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
        # Disable the close 'X' button while the pipeline is running
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint) if 'QtCore' in globals() else None

        self.error_message = ""

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
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Pipeline completed successfully!")
            self.accept()
        else:
            self.error_message = err_str
            self.reject()


class FrameDetailsDialog(QDialog):
    def __init__(self, frame_name, column_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Details for Frame: {frame_name}")
        self.resize(650, 400)

        layout = QVBoxLayout(self)

        title_label = QLabel(f"Attribute Breakdown for Frame {frame_name}")
        layout.addWidget(title_label)

        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.populate_data(column_data)

    def populate_data(self, column_data):
        valid_data = column_data.dropna()
        cameras = list(valid_data.index)
        
        self.table.setRowCount(len(cameras))
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Camera", "Pos X", "Pos Y", "Pos Z", "Rot X", "Rot Y", "Rot Z", "Focal"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        camera_values = {}
        for camera_name in cameras:
            attr_tuple = valid_data[camera_name]
            try:
                pos, rot, focal = attr_tuple
                px, py, pz = pos
                rx, ry, rz = rot
                camera_values[camera_name] = [px, py, pz, rx, ry, rz, focal]
            except (ValueError, TypeError):
                camera_values[camera_name] = None

        col_group_mappings = []
        for col_idx in range(7):
            val_counts = {}
            camera_val_map = {}
            
            for camera_name in cameras:
                vals = camera_values[camera_name]
                if vals is None:
                    continue
                v = vals[col_idx]
                
                matched_rep = None
                for rep_val in val_counts:
                    if abs(v - rep_val) < 1e-4:
                        matched_rep = rep_val
                        break
                
                if matched_rep is None:
                    val_counts[v] = [v]
                    camera_val_map[camera_name] = v
                else:
                    val_counts[matched_rep].append(v)
                    camera_val_map[camera_name] = matched_rep

            sorted_unique_vals = sorted(val_counts.keys(), key=lambda r: len(val_counts[r]), reverse=True)
            val_to_gid = {val: gid for gid, val in enumerate(sorted_unique_vals)}
            
            cam_to_gid = {}
            for camera_name in cameras:
                if camera_name in camera_val_map:
                    rep_v = camera_val_map[camera_name]
                    for rv, gid in val_to_gid.items():
                        if abs(rep_v - rv) < 1e-4:
                            cam_to_gid[camera_name] = gid
                            break
                else:
                    cam_to_gid[camera_name] = 0
            
            col_group_mappings.append(cam_to_gid)

        for row, camera_name in enumerate(cameras):
            self.table.setItem(row, 0, QTableWidgetItem(str(camera_name)))

            vals = camera_values[camera_name]
            if vals is not None:
                for col_idx, val in enumerate(vals):
                    item = QTableWidgetItem(f"{val:.5f}")
                    cell_gid = col_group_mappings[col_idx].get(camera_name, 0)
                    cell_color = self.parent().model.get_group_color(cell_gid)
                    item.setBackground(QBrush(cell_color))
                    self.table.setItem(row, col_idx + 1, item)
            else:
                self.table.setItem(row, 1, QTableWidgetItem(str(valid_data[camera_name])))
                for col in range(2, 8):
                    self.table.setItem(row, col, QTableWidgetItem("-"))

# --- Add this new class alongside your other dialog classes ---

class SettingsDialog(QDialog):
    def __init__(self, current_blender_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 180)

        self.blender_path = current_blender_path
        
        layout = QVBoxLayout(self)

        # Blender Installation Folder Section
        layout.addWidget(QLabel("<b>Select Blender Installation Folder :</b>"))
        folder_layout = QHBoxLayout()
        
        # Use QLineEdit instead of QLabel so it's a nice input box and directly editable
        self.folder_input = QLineEdit(self.blender_path if self.blender_path else "")
        self.folder_input.setPlaceholderText("Enter or browse for Blender path...")
        
        folder_btn = QPushButton("Browse Folder")
        folder_btn.clicked.connect(self.select_blender_folder)
        
        folder_layout.addWidget(self.folder_input, stretch=1)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)

        layout.addSpacing(20)

        # Bottom Buttons (Cancel / Save)
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("font-weight: bold; padding: 6px 16px;")
        self.save_btn.clicked.connect(self.on_save)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)

    def select_blender_folder(self):
        current_text = self.folder_input.text().strip()
        start_dir = str(Path(current_text).parent) if current_text and Path(current_text).exists() else ""
        
        dir_path = QFileDialog.getExistingDirectory(self, "Select Blender Installation Directory", start_dir)
        if dir_path:
            potential_exe = Path(dir_path) / "blender.exe"
            if potential_exe.exists():
                self.folder_input.setText(str(potential_exe))
            else:
                self.folder_input.setText(dir_path)

    def on_save(self):
        # Capture whatever the user typed or selected before closing
        self.blender_path = self.folder_input.text().strip()
        self.accept()

    def select_blender_folder(self):
        start_dir = str(Path(self.blender_path).parent) if self.blender_path else ""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Blender Installation Directory", start_dir)
        if dir_path:
            # Automatically look for blender.exe inside the selected folder or confirm path
            potential_exe = Path(dir_path) / "blender.exe"
            if potential_exe.exists():
                self.blender_path = str(potential_exe)
            else:
                # If they picked a root folder, keep the directory or let them point to it
                self.blender_path = dir_path
                
            self.folder_label.setText(self.blender_path)
            self.folder_label.setStyleSheet("color: black;")


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())