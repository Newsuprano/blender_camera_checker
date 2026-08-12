import json
import os
from pathlib import Path

def get_cache_path(filename="config_cache.json"):
    """Returns the path to a persistent cache file in the user's AppData folder."""
    app_data = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CameraChecker")
    os.makedirs(app_data, exist_ok=True)
    return Path(app_data) / filename

CONFIG_FILE = get_cache_path()

def load_cache():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(data):
    try:
        current_data = load_cache()
        current_data.update(data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=4)
    except Exception as e:
        print(f"Could not save cache: {e}")