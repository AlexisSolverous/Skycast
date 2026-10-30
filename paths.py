import os
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def is_frozen():
    """Return whether this app is running from a PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def resource_path(relative):
    """Find a bundled file in development or inside a PyInstaller app."""
    if is_frozen():
        # PyInstaller extracts bundled files into this temporary folder.
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = PROJECT_DIR
    return base_dir / relative


def user_data_dir():
    """Return the per-user folder where a packaged app can safely write files."""
    # Program Files may be read-only, so saved app data belongs in AppData.
    appdata = os.environ.get("APPDATA")
    if appdata:
        data_dir = Path(appdata) / "SkyCast"
    else:
        # This fallback also keeps the helper usable in tests and non-Windows dev.
        data_dir = Path.home() / "AppData" / "Roaming" / "SkyCast"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
