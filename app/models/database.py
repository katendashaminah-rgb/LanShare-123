from __future__ import annotations

import sqlite3
from pathlib import Path


def init_db(db_path: str | Path | None = None):
    db_file = Path(db_path) if db_path else Path(__file__).resolve().parents[2] / "database" / "lanshare.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            relative_path TEXT NOT NULL UNIQUE,
            folder TEXT,
            size INTEGER NOT NULL,
            mime_type TEXT,
            checksum TEXT,
            uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            source_device TEXT
        );

        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent TEXT,
            path TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            port INTEGER NOT NULL,
            version TEXT,
            last_seen TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            storage_used INTEGER,
            storage_limit INTEGER
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()
    return db_file


def get_db_connection(db_path: str | Path | None = None):
    db_file = Path(db_path) if db_path else Path(__file__).resolve().parents[2] / "database" / "lanshare.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
