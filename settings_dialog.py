from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, 
    QVBoxLayout, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QPushButton, 
    QSpinBox, 
    QFileDialog
)
from cache import load_cache, save_cache

class SettingsDialog(QDialog):
    def __init__(self, current_blender_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 240)  # Slightly taller to fit the new setting

        self.blender_path = current_blender_path
        
        layout = QVBoxLayout(self)

        # --- Blender Installation Folder Section ---
        layout.addWidget(QLabel("<b>Select Blender Installation Folder :</b>"))
        folder_layout = QHBoxLayout()
        
        self.folder_input = QLineEdit(self.blender_path if self.blender_path else "")
        self.folder_input.setPlaceholderText("Enter or browse for Blender path...")
        
        folder_btn = QPushButton("Browse Folder")
        folder_btn.clicked.connect(self.select_blender_folder)
        
        folder_layout.addWidget(self.folder_input, stretch=1)
        folder_layout.addWidget(folder_btn)
        layout.addLayout(folder_layout)

        layout.addSpacing(15)

        # --- Decimal Precision Section ---
        layout.addWidget(QLabel("<b>Decimal Places for Displayed Values :</b>"))
        self.decimal_spinbox = QSpinBox()
        self.decimal_spinbox.setRange(0, 6)
        
        # Load current precision from cache (defaults to 5 if not found)
        cache = load_cache()
        current_decimals = cache.get("decimal_places", 5)
        self.decimal_spinbox.setValue(current_decimals)
        
        layout.addWidget(self.decimal_spinbox)

        layout.addSpacing(20)

        # --- Bottom Buttons (Cancel / Save) ---
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
        # Capture the Blender path
        self.blender_path = self.folder_input.text().strip()
        
        # Capture and save the decimal places setting into your cache
        decimals = self.decimal_spinbox.value()
        cache = load_cache()
        cache["decimal_places"] = decimals
        save_cache(cache)
        
        self.accept()