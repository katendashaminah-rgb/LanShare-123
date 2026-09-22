from __future__ import annotations

from pathlib import Path


def format_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{size_bytes} B"


def safe_relative_path(value: str) -> str:
    cleaned = Path(value)
    if cleaned.is_absolute() or ".." in cleaned.parts:
        raise ValueError("Invalid path.")
    return cleaned.as_posix()
