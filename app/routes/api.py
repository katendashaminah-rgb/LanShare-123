from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from flask import Blueprint, Response, jsonify, redirect, request, send_file

from app.config import AppConfig
from app.models.database import get_db_connection, init_db
from app.services.storage import StorageManager

api_bp = Blueprint("api", __name__)


def get_storage_manager():
    storage_root = Path(os.getenv("LANSHARE_STORAGE_DIR", AppConfig.STORAGE_DIR)).expanduser()
    storage_root.mkdir(parents=True, exist_ok=True)
    return StorageManager(storage_root=storage_root, max_bytes=AppConfig.MAX_STORAGE_BYTES)


@api_bp.route("/api/status")
def api_status():
    manager = get_storage_manager()
    used = manager.get_used_bytes()
    return jsonify({
        "app_name": AppConfig.APP_NAME,
        "version": AppConfig.APP_VERSION,
        "port": AppConfig.PORT,
        "storage_used": used,
        "storage_limit": manager.max_bytes,
        "available": manager.get_available_bytes(),
    })


@api_bp.route("/api/files")
def api_files():
    manager = get_storage_manager()
    items = []
    for path in sorted(manager.storage_root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(manager.storage_root).as_posix()
            items.append({
                "name": path.name,
                "path": rel,
                "size": path.stat().st_size,
                "type": path.suffix.lower().lstrip("."),
            })
    return jsonify({"items": items})


@api_bp.route("/api/files", methods=["DELETE"])
def api_delete_file():
    manager = get_storage_manager()
    payload = request.get_json(silent=True) or {}
    rel_path = payload.get("path") or request.args.get("path")
    if not rel_path:
        return jsonify({"error": "A file path is required."}), 400
    try:
        deleted = manager.delete_file_record(rel_path)
        return jsonify({"status": "ok" if deleted else "missing", "path": rel_path})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/api/upload", methods=["POST"])
def api_upload():
    manager = get_storage_manager()
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file_obj = request.files["file"]
    filename = request.form.get("filename") or file_obj.filename
    if not filename:
        return jsonify({"error": "A valid filename is required."}), 400

    destination = request.form.get("folder", "")
    try:
        # File size is safe to read from the uploaded stream when available.
        size = file_obj.seek(0, os.SEEK_END)
        file_obj.seek(0)
        clean_name = manager.validate_upload(filename, size)
        rel_path = Path(destination) / clean_name if destination else Path(clean_name)
        resolved = manager.resolve_storage_path(rel_path)
        temp_path = resolved.with_suffix(resolved.suffix + ".part")
        file_obj.save(temp_path)
        temp_path.replace(resolved)
        relative_path = Path(rel_path).as_posix()
        return jsonify({
            "status": "ok",
            "path": relative_path,
            "relative_path": relative_path,
            "saved_to": str(resolved),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/api/download/<path:relative_path>")
def api_download(relative_path):
    manager = get_storage_manager()
    try:
        resolved = manager.resolve_storage_path(relative_path)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not resolved.exists() or not resolved.is_file():
        return jsonify({"error": "The requested file could not be found."}), 404
    return send_file(resolved, as_attachment=True, download_name=resolved.name)


@api_bp.route("/api/folders", methods=["POST"])
def create_folder():
    manager = get_storage_manager()
    name = request.json.get("name") if request.is_json else None
    if not name:
        return jsonify({"error": "Folder name is required."}), 400
    try:
        path = manager.create_folder(name)
        return jsonify({"status": "ok", "path": path.relative_to(manager.storage_root).as_posix()})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@api_bp.route("/api/discover")
def api_discover():
    from app.services.discovery import get_local_ip_addresses

    return jsonify({"devices": [{"device_name": AppConfig.DEVICE_NAME, "ip_address": ip, "port": AppConfig.PORT} for ip in get_local_ip_addresses()]})


@api_bp.route("/api/remote/files")
def api_remote_files():
    device_ip = request.args.get("device_ip") or request.args.get("host")
    if not device_ip:
        return jsonify({"error": "device_ip is required."}), 400
    try:
        with urlopen(f"http://{device_ip}:{AppConfig.PORT}/api/files", timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return jsonify(payload)
    except Exception as exc:
        return jsonify({"error": f"Could not reach device {device_ip}: {exc}"}), 502


@api_bp.route("/api/remote/download")
def api_remote_download():
    manager = get_storage_manager()
    device_ip = request.args.get("device_ip")
    rel_path = request.args.get("path")
    if not device_ip or not rel_path:
        return jsonify({"error": "device_ip and path are required."}), 400

    try:
        safe_rel = Path(rel_path)
        if safe_rel.is_absolute() or ".." in safe_rel.parts:
            raise ValueError("Invalid remote path.")
        target_dir = manager.storage_root / "Remote Downloads"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_rel.name
        if target_path.exists():
            target_path = target_dir / f"{safe_rel.stem}_copy{safe_rel.suffix}"

        remote_url = f"http://{device_ip}:{AppConfig.PORT}/api/download/{quote(safe_rel.as_posix())}"
        with urlopen(remote_url, timeout=20) as response, open(target_path, "wb") as destination:
            shutil.copyfileobj(response, destination)

        return jsonify({"status": "ok", "path": target_path.relative_to(manager.storage_root).as_posix()})
    except Exception as exc:
        return jsonify({"error": f"Remote download failed: {exc}"}), 502


@api_bp.route("/api/devices")
def api_devices():
    return jsonify({"devices": []})


@api_bp.route("/")
def index():
    return redirect("/dashboard")


@api_bp.route("/dashboard")
def dashboard_page():
    from flask import render_template
    return render_template("dashboard.html")


@api_bp.route("/files")
def files_page():
    from flask import render_template
    return render_template("files.html")


@api_bp.route("/devices")
def devices_page():
    from flask import render_template
    return render_template("devices.html")


@api_bp.route("/settings")
def settings_page():
    from flask import render_template
    return render_template("settings.html")
