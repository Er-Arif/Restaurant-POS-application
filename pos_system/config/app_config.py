from __future__ import annotations

import os
import sys
from pathlib import Path


APP_VENDOR = "CodexRetail"
APP_NAME = "WhiteLabelPOS"
APP_DISPLAY_NAME = "White-Label Restaurant POS"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return project_root()


def runtime_root() -> Path:
    override = os.environ.get("POS_RUNTIME_ROOT")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("PROGRAMDATA", Path.home() / "AppData" / "Local"))
        return base / APP_VENDOR / APP_NAME
    return project_root() / ".runtime"


DATA_DIR = runtime_root()
DB_DIR = DATA_DIR / "data"
DB_PATH = DB_DIR / "pos.db"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
LOGO_DIR = DATA_DIR / "branding"
LICENSE_DIR = DATA_DIR / "license"
LICENSE_FILE = LICENSE_DIR / "license.dat"
RECEIPT_PREVIEW_FILE = DATA_DIR / "last_receipt.txt"
BUNDLED_PUBLIC_KEY = resource_root() / "pos_system" / "license" / "public_key.pem"


def ensure_runtime_dirs() -> None:
    for path in (DATA_DIR, DB_DIR, BACKUP_DIR, EXPORT_DIR, LOGO_DIR, LICENSE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def bundled_asset(*parts: str) -> Path:
    return resource_root().joinpath(*parts)
