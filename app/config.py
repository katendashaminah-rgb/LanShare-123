from __future__ import annotations

import os
from pathlib import Path


class AppConfig:
    APP_NAME = "LANShare 50"
    APP_VERSION = "1.0.0"
    PORT = int(os.getenv("LANSHARE_PORT", "5000"))
    STORAGE_DIR = Path(os.getenv("LANSHARE_STORAGE_DIR", Path(__file__).resolve().parent.parent / "storage")).expanduser()
    MAX_STORAGE_BYTES = int(os.getenv("LANSHARE_MAX_STORAGE_BYTES", str(50_000_000_000)))
    DEVICE_NAME = os.getenv("LANSHARE_DEVICE_NAME", "LANShare-PC")
    DISCOVERY_INTERVAL_SECONDS = int(os.getenv("LANSHARE_DISCOVERY_INTERVAL", "5"))
    DEBUG = os.getenv("LANSHARE_DEBUG", "false").lower() in {"1", "true", "yes"}
    DATABASE_PATH = Path(os.getenv("LANSHARE_DB_PATH", Path(__file__).resolve().parent.parent / "database" / "lanshare.db")).expanduser()
    TEMP_UPLOAD_SUFFIX = ".part"
