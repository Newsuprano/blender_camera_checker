import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTableView
from logic import load_and_pivot_data, count_frame_statuses, create_mismatched_dataframe
from ui_table_model import CameraTableModel

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

    def on_toggle_mismatches(self, checked) :
        if checked :
            self.toggle_btn.show()
            self.model.update_data(self.mismatched_df)
            self.toggle_btn.setText("Show All Frames")
        else :
            self.model.update_data(self.pivot_df)
            self.toggle_btn.setText("Show Mismatches Only")


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())