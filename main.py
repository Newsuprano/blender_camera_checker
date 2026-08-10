import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableView, QHeaderView, QDialog, QLabel, QTableWidget, QTableWidgetItem 
from logic import load_and_pivot_data, count_frame_statuses, create_mismatched_dataframe, get_frame_clusters_tuple
from ui_table_model import CameraTableModel
from PyQt6.QtGui import QColor, QBrush

class MainWindow(QMainWindow) :
    def __init__(self) :
        super().__init__()
        self.setWindowTitle("Camera Sync Checker")
        self.resize(900, 600)

        self.pivot_df = load_and_pivot_data()
        _, _, bad_frames = count_frame_statuses(self.pivot_df)
        self.mismatched_df = create_mismatched_dataframe(self.pivot_df, bad_frames)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.toggle_btn = QPushButton("Show Mismatches Only")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self.on_toggle_mismatches)
        layout.addWidget(self.toggle_btn)

        self.table_view = QTableView()
        self.model = CameraTableModel(self.pivot_df)
        self.table_view.setModel(self.model)
        layout.addWidget(self.table_view)

        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        horizontal_header = self.table_view.horizontalHeader()
        horizontal_header.setSectionsClickable(True)
        horizontal_header.sectionClicked.connect(self.on_frame_header_clicked)

    def on_toggle_mismatches(self, checked) :
        if checked :
            self.toggle_btn.show()
            self.model.update_data(self.mismatched_df)
            self.toggle_btn.setText("Show All Frames")
        else :
            self.model.update_data(self.pivot_df)
            self.toggle_btn.setText("Show Mismatches Only")

    def on_frame_header_clicked(self, logical_index) :
        frame_name = self.model._df.columns[logical_index]
        column_data = self.model._df[frame_name]

        dialog = FrameDetailsDialog(frame_name, column_data, self)
        dialog.exec()


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
        # 8 columns total: Camera + 7 attributes (No Group column)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Camera", "Pos X", "Pos Y", "Pos Z", "Rot X", "Rot Y", "Rot Z", "Focal"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Step 1: Extract raw attribute tuples into a clean dictionary
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

        # Step 2: Independently cluster each attribute column, sorted by frequency (majority = Group 0)
        col_group_mappings = []
        for col_idx in range(7):
            # Count occurrences of each unique value in this column
            val_counts = {}
            camera_val_map = {}
            
            for camera_name in cameras:
                vals = camera_values[camera_name]
                if vals is None:
                    continue
                v = vals[col_idx]
                
                # Check against existing unique values using small tolerance
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

            # Sort unique values by frequency (largest group first, so it becomes Group 0)
            sorted_unique_vals = sorted(val_counts.keys(), key=lambda r: len(val_counts[r]), reverse=True)
            
            val_to_gid = {val: gid for gid, val in enumerate(sorted_unique_vals)}
            
            # Map each camera to its priority group ID for this specific column
            cam_to_gid = {}
            for camera_name in cameras:
                if camera_name in camera_val_map:
                    rep_v = camera_val_map[camera_name]
                    # Find matching sorted value
                    for rv, gid in val_to_gid.items():
                        if abs(rep_v - rv) < 1e-4:
                            cam_to_gid[camera_name] = gid
                            break
                else:
                    cam_to_gid[camera_name] = 0
            
            col_group_mappings.append(cam_to_gid)

        # Step 3: Populate table rows with clean column-independent priority colors
        for row, camera_name in enumerate(cameras):
            # Column 0: Camera Name
            self.table.setItem(row, 0, QTableWidgetItem(str(camera_name)))

            vals = camera_values[camera_name]
            if vals is not None:
                # Columns 1 to 7: Individual attributes mapped to frequency-based priority groups
                for col_idx, val in enumerate(vals):
                    item = QTableWidgetItem(f"{val:.3f}")
                    
                    # Get priority group ID (0 = majority/green, 1+ = minority/red/yellow)
                    cell_gid = col_group_mappings[col_idx].get(camera_name, 0)
                    cell_color = self.parent().model.get_group_color(cell_gid)
                    item.setBackground(QBrush(cell_color))
                    
                    # Offset by 1 because column 0 is just the Camera Name now
                    self.table.setItem(row, col_idx + 1, item)
            else:
                # Fallback if unpacking failed
                self.table.setItem(row, 1, QTableWidgetItem(str(valid_data[camera_name])))
                for col in range(2, 8):
                    self.table.setItem(row, col, QTableWidgetItem("-"))


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())