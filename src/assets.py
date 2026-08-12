import sys
import os
from pathlib import Path

def get_ressource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundled apps"""
    try:
        # PyInstaller creates a temp folder and stores the path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a bundled .exe, anchor it to the project root 
        base_path = Path(__file__).resolve().parent.parent
        
    return os.path.join(base_path, relative_path)