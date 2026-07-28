"""
Configuration — adapts to dev mode vs packaged desktop app.
"""

import sys
import os
from pathlib import Path


def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def _get_bundle_dir() -> Path:
    """Where the exe or script lives."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _get_data_dir() -> Path:
    """Where uploads, db, processed files go."""
    if _is_frozen():
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        data_dir = Path(appdata) / "MedicalPDFAnnotator"
    else:
        data_dir = Path(__file__).resolve().parent.parent

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _find_static_dir() -> Path:
    """
    Find the built frontend files.
    PyInstaller might put them in different locations.
    """
    bundle = _get_bundle_dir()

    # Check multiple possible locations
    candidates = [
        bundle / "static",
        bundle / "backend" / "static",
        bundle / "_internal" / "static",
    ]

    # Also check _MEIPASS (PyInstaller temp dir)
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.insert(0, Path(meipass) / "static")
        candidates.insert(1, Path(meipass) / "backend" / "static")

    for candidate in candidates:
        if candidate.exists() and (candidate / "index.html").exists():
            return candidate

    # Fallback — might not exist in dev mode
    return bundle / "static"


# ── Directories ──
BUNDLE_DIR = _get_bundle_dir()
DATA_DIR = _get_data_dir()

UPLOAD_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
LOG_DIR = DATA_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"
DATABASE_PATH = DATA_DIR / "annotator.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

STATIC_DIR = _find_static_dir()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Retention limits
MAX_PROCESSED_AGE_DAYS = 30
MAX_LOG_AGE_DAYS = 7

# Page rendering defaults
DEFAULT_ZOOM = 1.5
THUMBNAIL_WIDTH = 120
MAX_UPLOAD_SIZE = 500 * 1024 * 1024

IS_FROZEN = _is_frozen()