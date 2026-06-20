"""
Direct Google Drive client used in Phase 1 before the MCP server is built.
All functions mirror the MCP tool signatures so refactoring to MCP later is a
simple swap — agents call the same function names either way.
"""

import io
import json
from functools import lru_cache
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from backend.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
_FOLDER_CACHE: dict[str, str] = {}


@lru_cache(maxsize=1)
def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _get_or_create_subfolder(folder_name: str) -> str:
    """Return the Drive folder ID for a subfolder under the root, creating it if needed."""
    if folder_name in _FOLDER_CACHE:
        return _FOLDER_CACHE[folder_name]

    service = _get_service()
    query = (
        f"name='{folder_name}' and "
        f"'{settings.drive_folder_id}' in parents and "
        f"mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
    else:
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [settings.drive_folder_id],
        }
        folder = service.files().create(body=metadata, fields="id").execute()
        folder_id = folder["id"]

    _FOLDER_CACHE[folder_name] = folder_id
    return folder_id


def _get_file_id(folder_id: str, filename: str) -> str | None:
    service = _get_service()
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def store_read_json(folder: str, filename: str) -> dict:
    """Read and parse a JSON file from a Drive subfolder."""
    service = _get_service()
    folder_id = _get_or_create_subfolder(folder)
    file_id = _get_file_id(folder_id, filename)

    if not file_id:
        return {}

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return json.loads(buffer.getvalue().decode("utf-8"))


def store_write_json(folder: str, filename: str, data: dict) -> None:
    """Write a dict as JSON to Drive, creating or updating the file."""
    service = _get_service()
    folder_id = _get_or_create_subfolder(folder)
    file_id = _get_file_id(folder_id, filename)

    content = json.dumps(data, indent=2, default=str).encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/json")

    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": filename, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media, fields="id").execute()


def store_append_record(folder: str, filename: str, record: dict, array_key: str) -> None:
    """Append a record to a JSON array inside a file."""
    data = store_read_json(folder, filename)
    if array_key not in data:
        data[array_key] = []
    data[array_key].append(record)
    from datetime import datetime, timezone
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    store_write_json(folder, filename, data)


def store_update_record(
    folder: str, filename: str, record_id: str, updates: dict, array_key: str
) -> bool:
    """Find a record by id and patch its fields. Returns True if found."""
    data = store_read_json(folder, filename)
    records = data.get(array_key, [])
    for i, record in enumerate(records):
        if record.get("id") == record_id:
            records[i] = {**record, **updates}
            from datetime import datetime, timezone
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            store_write_json(folder, filename, data)
            return True
    return False


def store_delete_record(
    folder: str, filename: str, record_id: str, array_key: str
) -> bool:
    """Remove a record from a JSON array. Returns True if found and removed."""
    data = store_read_json(folder, filename)
    records = data.get(array_key, [])
    original_len = len(records)
    data[array_key] = [r for r in records if r.get("id") != record_id]
    if len(data[array_key]) < original_len:
        from datetime import datetime, timezone
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        store_write_json(folder, filename, data)
        return True
    return False
