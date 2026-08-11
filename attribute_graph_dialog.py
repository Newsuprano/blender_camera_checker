import pyqtgraph as pg
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

class AttributeGraphDialog(QDialog):
    def __init__(self, attribute_name, col_idx, all_frames_data, parent=None):
        super().__init__(parent)
        self.attribute_name = attribute_name
        self.col_idx = col_idx
        self.all_frames_data = all_frames_data
        
        self.setWindowTitle(f"Trend: {attribute_name}")
        self.resize(900, 600)
        
        main_layout = QHBoxLayout(self)
        
        # Setup PyQtGraph plot widget first
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', attribute_name)
        self.plot_widget.setLabel('bottom', 'Frame Number')
        self.plot_widget.showGrid(x=True, y=True)
        
        # Calculate total frames and set the clear title dynamically
        frames = sorted(list(self.all_frames_data.keys()))
        total_frames_count = len(frames)
        self.plot_widget.setTitle(f'Evolution of {attribute_name} over {total_frames_count} frames', color="w", size="11pt")
        
        main_layout.addWidget(self.plot_widget, stretch=4)
        
        # Setup Sidebar for Toggles
        sidebar_widget = QWidget()
        self.checkbox_layout = QVBoxLayout(sidebar_widget)
        self.checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignTop) if hasattr(Qt, 'AlignmentFlag') else self.checkbox_layout.setAlignment(Qt.Alignment.AlignTop)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(sidebar_widget)
        main_layout.addWidget(scroll_area, stretch=1)
        
        self.curves = {}
        self.plot_data()

    def plot_data(self):
        # Extract all unique frames and sort them
        frames = sorted(list(self.all_frames_data.keys()))
        
        all_cameras = set()
        for frame in frames:
            valid_data = self.all_frames_data[frame]
            if hasattr(valid_data, "index"):
                all_cameras.update(valid_data.index)

        all_cameras = sorted(list(all_cameras))
        
        total_cams = max(len(all_cameras), 1)
        for idx, cam_name in enumerate(all_cameras):
            hue = int((idx * 360.0) / total_cams)
            color = QColor.fromHsv(hue, 200, 255)
            pen = pg.mkPen(color=color, width=2)

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

            curve_item = self.plot_widget.plot(x_vals, y_vals, pen=pen, name=str(cam_name))
            self.curves[cam_name] = {
                "item": curve_item,
                "x": x_vals,
                "y": y_vals
            }

            # Create checkbox with palette-based text coloring
            checkbox = QCheckBox(str(cam_name))
            checkbox.setChecked(True)
            
            palette = checkbox.palette()
            palette.setColor(palette.ColorRole.WindowText, color)
            checkbox.setPalette(palette)
            
            checkbox.stateChanged.connect(lambda state, cn=cam_name: self.toggle_camera_curve(cn, state))
            self.checkbox_layout.addWidget(checkbox)

        self.checkbox_layout.addStretch()

    def toggle_camera_curve(self, cam_name, state):
        if cam_name not in self.curves:
            return
        
        curve_info = self.curves[cam_name]
        item = curve_info["item"]
        
        # Handle PyQt6 vs PyQt5 state check safely
        is_checked = state == 2 or state is True
        
        if is_checked:
            item.setData(curve_info["x"], curve_info["y"])
        else:
            item.setData([], [])