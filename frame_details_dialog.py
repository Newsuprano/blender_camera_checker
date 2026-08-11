from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QHeaderView, 
    QDialog, 
    QLabel, 
    QTableWidget, 
    QTableWidgetItem, 
)
from PyQt6.QtGui import QColor, QBrush
from attribute_graph_dialog import AttributeGraphDialog

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

        self.table.setSortingEnabled(False)
        
        # Configure the horizontal header
        header = self.table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionDoubleClicked.connect(self.on_column_header_double_clicked)

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
                    total_groups_in_col = len(val_counts)

                    cell_color = self.parent().model.get_dynamic_group_color(cell_gid, total_groups_in_col)

                    item.setBackground(QBrush(cell_color))
                    item.setForeground(QBrush(self.get_contrasted_text_color(cell_color)))

                    self.table.setItem(row, col_idx + 1, item)
            else:
                self.table.setItem(row, 1, QTableWidgetItem(str(valid_data[camera_name])))
                for col in range(2, 8):
                    self.table.setItem(row, col, QTableWidgetItem("-"))

    def get_contrasted_text_color(self, bg_color):
        # Standard luminance formula
        luminance = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue()) / 255
        if luminance > 0.5:
            return QColor(0, 0, 0)       # Dark text for bright backgrounds
        else:
            return QColor(255, 255, 255) # White text for dark backgrounds

    def on_column_header_double_clicked(self, logical_index):
        if logical_index == 0:
            return

        headers = ["Camera", "Pos X", "Pos Y", "Pos Z", "Rot X", "Rot Y", "Rot Z", "Focal"]
        attr_name = headers[logical_index]
        attr_col_idx = logical_index - 1 

        main_window = self.parent()
        
        # Grab the full multi-frame dataframe from your main window or its model
        # (Change 'model' or '_df' to match whatever your main window calls it)
        full_df = getattr(main_window, "_df", None)
        if full_df is None and hasattr(main_window, "model"):
            full_df = getattr(main_window.model, "_df", None)

        if full_df is None:
            print("Error: Could not find the main dataframe.")
            return

        self.graph_dialog = AttributeGraphDialog(
            attribute_name=attr_name, 
            col_idx=attr_col_idx, 
            all_frames_data=full_df, 
            parent=self
        )
        self.graph_dialog.show()