import json
from pathlib import Path

CONFIG_FILE = Path("config_cache.json")

def load_cache():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(data):
    try:
        current_data = load_cache()
        current_data.update(data)
        with open(CONFIG_FILE, "w") as f:
            json.dump(current_data, f, indent=4)
    except Exception as e:
        print(f"Could not save cache: {e}")