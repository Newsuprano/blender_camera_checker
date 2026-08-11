from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,
    QDialog, 
    QCheckBox,
    QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pyqtgraph as pg

class AttributeGraphDialog(QDialog):
    def __init__(self, attribute_name, col_idx, all_frames_data, parent=None):
        super().__init__(parent)
        self.attribute_name = attribute_name
        self.col_idx = col_idx
        self.all_frames_data = all_frames_data  # Structure mapping frames to their camera attributes
        
        self.setWindowTitle(f"Behavior Over Time: {attribute_name}")
        self.resize(900, 600)
        
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)

        # 1. Plot Widget on the left
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e') # Match your dark theme
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', self.attribute_name)
        self.plot_widget.setLabel('bottom', 'Frame Index')
        layout.addWidget(self.plot_widget, stretch=4)

        # 2. Sidebar with checkable camera curves on the right
        sidebar_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.checkbox_container = QWidget()
        self.checkbox_layout = QVBoxLayout(self.checkbox_container)
        scroll_area.setWidget(self.checkbox_container)
        
        sidebar_layout.addWidget(scroll_area)
        layout.addLayout(sidebar_layout, stretch=1)

        self.curves = {} # Stores {camera_name: (plot_curve_item, data_x, data_y, color)}
        self.plot_data()

    def plot_data(self):
        # Extract all unique frames and sort them
        frames = sorted(list(self.all_frames_data.keys()))
        
        # Discover all unique cameras across these frames
        all_cameras = set()
        for frame in frames:
            valid_data = self.all_frames_data[frame]
            if hasattr(valid_data, "index"):
                all_cameras.update(valid_data.index)

        all_cameras = sorted(list(all_cameras))
        
        # Generate distinct colors for each camera
        total_cams = max(len(all_cameras), 1)
        for idx, cam_name in enumerate(all_cameras):
            hue = int((idx * 360.0) / total_cams)
            color = QColor.fromHsv(hue, 200, 255)
            pen = pg.mkPen(color=color, width=2)

            # Collect X (frames) and Y (attribute values) for this camera
            x_vals = []
            y_vals = []

            for frame in frames:
                valid_data = self.all_frames_data[frame]
                try:
                    if cam_name in valid_data.index:
                        attr_tuple = valid_data[cam_name]
                        pos, rot, focal = attr_tuple
                        flat_vals = list(pos) + list(rot) + [focal]
                        val = flat_vals[self.col_idx]
                        
                        x_vals.append(int(frame))
                        y_vals.append(float(val))
                except Exception:
                    continue

            # Plot the curve
            curve_item = self.plot_widget.plot(x_vals, y_vals, pen=pen, name=str(cam_name))
            self.curves[cam_name] = {
                "item": curve_item,
                "x": x_vals,
                "y": y_vals
            }

            # Create a toggle checkbox in the sidebar
            checkbox = QCheckBox(str(cam_name))
            checkbox.setChecked(True)

            # Create a toggle checkbox in the sidebar
            checkbox = QCheckBox(str(cam_name))
            checkbox.setChecked(True)
            
            # Use palette for text color so it never affects the native checkmark
            palette = checkbox.palette()
            palette.setColor(palette.ColorRole.WindowText, color)
            checkbox.setPalette(palette)
            
            checkbox.stateChanged.connect(lambda state, cn=cam_name: self.toggle_camera_curve(cn, state))
            self.checkbox_layout.addWidget(checkbox)

        self.checkbox_layout.addStretch()

    def toggle_camera_curve(self, camera_name, state):
        curve_info = self.curves.get(camera_name)
        if not curve_info:
            return
        
        item = curve_info["item"]
        if state == Qt.CheckState.Checked.value:
            item.setData(curve_info["x"], curve_info["y"]) # Restore data
        else:
            item.setData([], []) # Clear data to hide curve