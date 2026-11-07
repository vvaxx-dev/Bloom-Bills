
import os
import sys
from pathlib import Path

APP_FOLDER = "BloomAndBills"


def resource_path(relative):
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / relative


def save_dir():
    override = os.environ.get("BLOOM_SAVE_DIR")
    if override:
        folder = Path(override)
    elif sys.platform == "darwin":
        folder = Path.home() / "Library" / "Application Support" / APP_FOLDER
    elif sys.platform.startswith("win"):
        folder = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_FOLDER
    else:
        folder = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / APP_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    return folder
