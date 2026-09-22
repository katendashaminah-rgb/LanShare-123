from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO


class StorageManager:
    """Manage the application-controlled storage root and file metadata."""

    MAX_STORAGE_BYTES = 50_000_000_000

    def __init__(self, storage_root: str | Path, max_bytes: int | None = None):
        self.storage_root = Path(storage_root).expanduser().resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes if max_bytes is not None else self.MAX_STORAGE_BYTES
        self.max_storage_bytes = self.max_bytes

    def resolve_storage_path(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)

        if candidate.is_absolute():
            raise ValueError("Absolute paths are not allowed.")
        if ".." in candidate.parts:
            raise ValueError("Path traversal is not allowed.")
        if any(part in {"", "."} for part in candidate.parts):
            pass

        target = (self.storage_root / candidate).resolve()
        if self.storage_root not in target.parents and target != self.storage_root:
            raise ValueError("Requested path is outside the storage directory.")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def get_used_bytes(self) -> int:
        total = 0
        for path in self.storage_root.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def get_available_bytes(self) -> int:
        return max(0, self.max_bytes - self.get_used_bytes())

    def has_capacity(self, incoming_size: int) -> bool:
        if incoming_size < 0:
            return False
        return self.get_used_bytes() + incoming_size <= self.max_bytes

    def validate_upload(self, filename: str, size: int) -> str:
        if not filename or not filename.strip():
            raise ValueError("A valid filename is required.")

        candidate = Path(filename)
        if candidate.is_absolute() or any(part in {"..", ""} for part in candidate.parts):
            raise ValueError("Invalid filename.")
        if filename.startswith("/") or filename.startswith("\\"):
            raise ValueError("Invalid filename.")
        if "/" in filename or "\\" in filename:
            raise ValueError("Folder paths are not allowed in filenames.")

        clean_filename = candidate.name
        if clean_filename in {"", ".", ".."}:
            raise ValueError("Invalid filename.")
        if size < 0:
            raise ValueError("File size cannot be negative.")
        if not self.has_capacity(size):
            raise ValueError("The upload cannot be completed because there is not enough storage space.")
        return clean_filename

    def create_folder(self, folder_name: str | Path) -> Path:
        folder_path = self.resolve_storage_path(folder_name)
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path

    def delete_folder(self, folder_name: str | Path) -> bool:
        target = self.resolve_storage_path(folder_name)
        if not target.exists():
            return False
        if not target.is_dir():
            raise ValueError("The target is not a directory.")
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink(missing_ok=True)
        for child in sorted(target.rglob("*"), reverse=True):
            if child.is_dir():
                child.rmdir()
        target.rmdir()
        return True

    def create_file_record(self, filename: str, relative_path: str | Path, size: int, content_type: str, checksum: str) -> Path:
        target = self.resolve_storage_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return target
        target.write_bytes(b"")
        return target

    def get_file_record(self, relative_path: str | Path):
        target = self.resolve_storage_path(relative_path)
        if not target.exists():
            return None
        return target

    def delete_file_record(self, relative_path: str | Path) -> bool:
        target = self.resolve_storage_path(relative_path)
        if not target.exists():
            return False
        target.unlink()
        return True

    def prepare_duplicate_target(self, relative_path: str | Path):
        path = Path(relative_path)
        target = self.resolve_storage_path(path)
        if not target.exists():
            return str(target), "new"
        return str(target), "duplicate"

    def start_temp_upload(self, relative_path: str | Path) -> Path:
        target = self.resolve_storage_path(relative_path)
        temp_path = target.with_suffix(target.suffix + ".part")
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.touch()
        return temp_path

    def cleanup_temp_upload(self, temp_path: str | Path) -> None:
        path = Path(temp_path)
        if path.exists():
            path.unlink()

    def stream_upload_to_path(self, incoming: BinaryIO, relative_path: str | Path) -> Path:
        target = self.resolve_storage_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target.with_suffix(target.suffix + ".part")
        with open(temp_path, "wb") as dest:
            while True:
                chunk = incoming.read(1024 * 1024)
                if not chunk:
                    break
                dest.write(chunk)
        final_path = target
        temp_path.replace(final_path)
        return final_path

    def checksum_for_file(self, file_path: str | Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
