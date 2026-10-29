import json
import os

from core.utils import get_config_path

CONFIG_FILE = get_config_path()

_MODE_DEFAULTS = {
    "photo": {"color_mode": "Custom", "width": 85, "transparency": "white", "overdrive_val": "2000"},
    "video": {"color_mode": "Color", "width": 85, "transparency": "black", "overdrive_val": "2500"},
    "game": {"color_mode": "Color", "width": 100, "transparency": "black", "overdrive_val": "3000"},
    "voxel": {"color_mode": "Color", "width": 120, "transparency": "black", "overdrive_val": "3000"},
}
_SHARED_MODE_DEFAULTS = {"fullcolor_style": "Blocky", "overdrive": False, "custom_color": "#8AA090"}


def default_settings():
    settings = {
        "theme": "Dark",
        "ascii_charset": "Standard",
        "deck_mode": "Image",
        "deck_height": 180,
        "photo_cutoff": 30,
        "voxel_preset": "torus",
        "voxel_spin": 30,
    }
    for mode, extra in _MODE_DEFAULTS.items():
        for key, value in {**_SHARED_MODE_DEFAULTS, **extra}.items():
            settings[f"{mode}_{key}"] = value
    return settings


def load_settings():
    settings = default_settings()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                settings.update(json.load(f))
        except Exception:
            pass
    return settings


def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass
