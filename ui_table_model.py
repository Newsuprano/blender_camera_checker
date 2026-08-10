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
                return QBrush(self.get_group_color(group_id))

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole) :
        if role == Qt.ItemDataRole.DisplayRole :
            if orientation == Qt.Orientation.Horizontal :
                return str(self._df.columns[section])
            elif orientation == Qt.Orientation.Vertical :
                return str(self._df.index[section])
        return None

    def get_group_color(self, group_id):
        palette = [
            QColor(150, 255, 150),   # Neon Green (Group 0 - Matched)
            QColor(255, 100, 100),   # Intense Red (Group 1 - Mismatch)
            QColor(255, 255, 100),   # Bright Yellow (Group 2)
            QColor(100, 200, 255),   # Vivid Cyan (Group 3)
            QColor(200, 150, 255),   # Bright Purple (Group 4)
        ]
        return palette[group_id % len(palette)]

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