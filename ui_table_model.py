from PyQt6.QtCore import QAbstractTableModel, Qt
from PyQt6.QtGui import QColor, QBrush, QIcon, QPixmap
from logic import get_frame_clusters_tuple

class CameraTableModel(QAbstractTableModel) :
    def __init__(self, df) :
        super().__init__()
        self._df = df

        self.cluster_cache = {}
        self.precompute_clusters()

    def precompute_clusters(self) :
        self.cluster_cache.clear()
        for frame in self._df.columns:
            self.cluster_cache[frame] = get_frame_clusters_tuple(self._df[frame])

    def update_data(self, new_df) :
        self.beginResetModel()
        self._df = new_df
        self.precompute_clusters()
        self.endResetModel()

    def rowCount(self, parent=None) :
        return len(self._df.index)

    def columnCount(self, parent=None) :
        return len(self._df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole) :
        if not index.isValid() :
            return None

        row = index.row()
        col = index.column()

        camera_name = self._df.index[row]
        frame_name = self._df.columns[col]

        if role == Qt.ItemDataRole.DisplayRole :
            return None

        elif role == Qt.ItemDataRole.BackgroundRole :
            frame_clusters = self.cluster_cache.get(frame_name, {})
            if camera_name in frame_clusters :
                group_id = frame_clusters[camera_name]["group_id"]

                total_groups = len(frame_clusters)
                brush_color = self.get_dynamic_group_color(group_id, total_groups)
                return QBrush(brush_color)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole) :
        if role == Qt.ItemDataRole.DisplayRole :
            if orientation == Qt.Orientation.Horizontal :
                return str(self._df.columns[section])
            elif orientation == Qt.Orientation.Vertical :
                return str(self._df.index[section])
        return None

    def get_dynamic_group_color(self, group_id, total_groups):
        # Keep your exact consensus color for Group 0
        if group_id == 0:
            return QColor(150, 255, 150)   # Neon Green

        # Predefined high-saturation palette fallback for up to group 4
        preset_palette = [
            QColor(150, 255, 150),   # Group 0: Neon Green
            QColor(255, 100, 100),   # Group 1: Intense Red
            QColor(255, 255, 100),   # Group 2: Bright Yellow
            QColor(100, 200, 255),   # Group 3: Vivid Cyan
            QColor(200, 150, 255),   # Group 4: Bright Purple
        ]

        if group_id < len(preset_palette):
            return preset_palette[group_id]

        # For 5+ groups, generate fully saturated, bright colors dynamically 
        # using the golden ratio hue distribution (~137.5 degrees apart)
        golden_ratio_conjugate = 0.618033988749895
        hue = (group_id * golden_ratio_conjugate) % 1.0
        
        # Convert normalized hue (0.0 - 1.0) to degrees (0 - 359)
        hue_deg = int(hue * 360)
        
        # Maximum saturation (255) and high value (255) to keep them neon/vivid like your palette
        return QColor.fromHsv(hue_deg, 205, 255)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(self._df.columns[section])
                
        elif orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                # Returns the camera name (e.g., "Camera01")
                return str(self._df.index[section])
            
            elif role == Qt.ItemDataRole.DecorationRole:
                # Adds a small icon to the left of the vertical header text
                # You can point this to a local "blender_icon.png" or use a standard style icon
                return QIcon("blender_icon.png") # Or QIcon.fromTheme("applications-other") as a fallback

        return super().headerData(section, orientation, role)