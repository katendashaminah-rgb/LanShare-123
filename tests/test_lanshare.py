import io
import json
from pathlib import Path

import pytest

from app import create_app
from app.models.database import init_db
from app.services.storage import StorageManager


@pytest.fixture
def temp_storage(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    return root


def test_storage_calculation_and_capacity_validation(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)

    assert manager.max_storage_bytes == 50_000_000_000
    assert manager.get_used_bytes() == 0
    assert manager.get_available_bytes() == 50_000_000_000
    assert manager.has_capacity(1_000) is True
    assert manager.has_capacity(50_000_000_000) is True
    assert manager.has_capacity(50_000_000_001) is False

    docs = temp_storage / "Documents"
    docs.mkdir()
    sample = docs / "sample.txt"
    sample.write_bytes(b"hello world")

    assert manager.get_used_bytes() >= 11
    assert manager.get_available_bytes() <= 50_000_000_000


def test_folder_creation_and_deletion(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)

    created = manager.create_folder("Projects/Alpha")
    assert created.exists()
    assert created.is_dir()

    empty = manager.delete_folder("Projects/Alpha")
    assert empty is True
    assert not (temp_storage / "Projects" / "Alpha").exists()


def test_file_delete_download_and_duplicate_handling(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)
    file_path = manager.create_file_record(
        filename="dup.txt",
        relative_path="Documents/dup.txt",
        size=12,
        content_type="text/plain",
        checksum="abc123",
    )

    assert file_path.exists()
    assert manager.get_file_record("Documents/dup.txt") is not None

    result = manager.prepare_duplicate_target("Documents/dup.txt")
    assert result[0].endswith("dup.txt")

    assert manager.delete_file_record("Documents/dup.txt") is True
    assert manager.get_file_record("Documents/dup.txt") is None


def test_path_traversal_prevention(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)

    with pytest.raises(ValueError):
        manager.resolve_storage_path("../../Windows/System32")

    with pytest.raises(ValueError):
        manager.resolve_storage_path("C:/Windows/System32")

    safe = manager.resolve_storage_path("Documents/report.pdf")
    assert safe.is_relative_to(temp_storage)


def test_database_operations(tmp_path):
    db_path = tmp_path / "lanshare.db"
    init_db(str(db_path))

    from app.models.database import get_db_connection

    with get_db_connection(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO files (filename, original_filename, relative_path, folder, size, mime_type, checksum, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
            ("note.txt", "note.txt", "Documents/note.txt", "Documents", 42, "text/plain", "check"),
        )
        conn.commit()

        row = conn.execute("SELECT filename FROM files WHERE relative_path = ?", ("Documents/note.txt",)).fetchone()
        assert row is not None
        assert row[0] == "note.txt"


def test_discovery_payload():
    from app.services.discovery import build_discovery_payload

    payload = build_discovery_payload(
        device_name="Alpha-PC",
        ip_address="192.168.1.10",
        port=5000,
        version="1.0.0",
        storage_used=12_500_000_000,
        storage_limit=50_000_000_000,
    )

    assert payload["device_name"] == "Alpha-PC"
    assert payload["ip_address"] == "192.168.1.10"
    assert payload["port"] == 5000
    assert payload["version"] == "1.0.0"


def test_app_status_and_file_listing(temp_storage):
    import os

    os.environ["LANSHARE_STORAGE_DIR"] = str(temp_storage)
    app = create_app({"TESTING": True, "MAX_STORAGE_BYTES": 50_000_000_000})
    client = app.test_client()

    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert resp.get_json()["app_name"] == "LANShare 50"

    files = client.get("/api/files")
    assert files.status_code == 200
    assert isinstance(files.get_json()["items"], list)


def test_invalid_upload_and_large_file_safety(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)

    with pytest.raises(ValueError):
        manager.validate_upload("", 10)

    with pytest.raises(ValueError):
        manager.validate_upload("../evil.txt", 10)

    with pytest.raises(ValueError):
        manager.validate_upload("bad\\name.txt", 10)

    large = io.BytesIO(b"a" * 1_048_576)
    target = temp_storage / "Documents"
    target.mkdir(exist_ok=True)
    saved = manager.stream_upload_to_path(large, "Documents/large.bin")
    assert saved.exists()
    assert saved.stat().st_size == 1_048_576


def test_interrupted_upload_cleanup(temp_storage):
    manager = StorageManager(storage_root=str(temp_storage), max_bytes=50_000_000_000)
    temp_path = manager.start_temp_upload("Documents/broken.bin")
    assert temp_path.exists()

    manager.cleanup_temp_upload(temp_path)
    assert not temp_path.exists()
