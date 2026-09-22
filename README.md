# LANShare 50

LANShare 50 is a simple, local-only file sharing application for computers connected to the same LAN. It supports discovery, browsing, upload, download, folder management, search, and storage quota enforcement without requiring internet access or a remote server.

## Features

- LAN discovery via UDP broadcast
- File and folder browsing inside a managed local storage directory
- Upload and download with streaming-safe handling
- Folder creation and deletion
- File deletion and duplicate-file conflict handling
- Search over metadata
- 50 GB capacity enforcement
- SQLite-backed metadata storage
- Simple web interface with HTML, CSS, and vanilla JavaScript
- PyInstaller-ready packaging for Windows

## Requirements

- Python 3.11+
- Flask
- SQLite
- Windows-friendly local networking

## Quick start

```bash
py -3 -m pip install -r requirements.txt
py -3 run.py
```

Then open the app in a browser at:

- http://localhost:5000
- or http://<your-computer-ip>:5000

## Configuration

The default configuration is defined in `app/config.py` and supports environment overrides:

```bash
set LANSHARE_PORT=5000
set LANSHARE_STORAGE_DIR=C:\LANShare\storage
set LANSHARE_MAX_STORAGE_BYTES=50000000000
set LANSHARE_DEVICE_NAME=My-PC
```

The app uses a storage directory managed under the project root by default.

## 50 GB limit

The app defines its storage limit as 50,000,000,000 bytes.

Before accepting an upload:

- current usage + file size <= MAX_STORAGE_BYTES
- otherwise the upload is rejected

This prevents users from exceeding the allowed capacity.

## Security model

- Path traversal attempts are rejected.
- Absolute paths are blocked.
- Files are restricted to the application storage directory.
- Download requests are verified against the storage root before sending.
- Temporary uploads are cleaned up if something fails.

## API endpoints

- GET /
- GET /dashboard
- GET /files
- GET /devices
- GET /settings
- GET /api/status
- GET /api/files
- POST /api/upload
- GET /api/download/<path:relative_path>
- POST /api/folders
- GET /api/discover
- GET /api/devices

## LAN discovery

LANShare devices listen for discovery requests and expose their device name, IP address, port, and version. This works on Wi-Fi and Ethernet LANs without internet access.

Windows Firewall may need to allow the app on the chosen port for local discovery to work across the network.

## Packaging with PyInstaller

From the project root:

```bash
py -3 -m PyInstaller --onefile --name LANShare50 run.py
```

The generated executable can be distributed as a standalone Windows app.

## Testing

```bash
py -3 -m pytest -q
```

The test suite covers:

- storage calculation
- capacity enforcement
- upload validation
- folder creation/deletion
- file deletion
- path traversal prevention
- duplicate handling
- SQLite operations
- discovery payloads

## Troubleshooting

- If the app cannot bind to a port, confirm it is free.
- If discovery does not work, ensure the Windows firewall is not blocking the app.
- If uploads fail, check storage space and file permissions.
- If downloads fail, verify the file path stays inside the storage root.

## Notes

LANShare 50 is intentionally simple and maintainable. It avoids unnecessary frameworks and keeps file content on disk rather than in SQLite.
