"""
Google Sheets data client — mirrors the drive_client.py interface exactly.
Used when DATA_STORE=sheets. Each logical "file" maps to a worksheet tab.

Sheet tab layout (auto-created on first use):
  grocery_items      — grocery list items
  purchase_history   — purchased items archive
  events             — family events
  todos              — household tasks
  family_profile     — family members & preferences
  agent_state        — orchestrator recovery state

Switch between this and drive_client.py via DATA_STORE env var.
"""

import json
import logging
from datetime import datetime, timezone
from functools import lru_cache

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from backend.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Maps (folder, filename) → list of (array_key, worksheet_tab_name)
_FILE_TAB_MAP: dict[tuple[str, str], dict[str, str]] = {
    ("groceries", "grocery_list.json"): {
        "items": "grocery_items",
        "purchase_history": "purchase_history",
    },
    ("events", "events.json"): {
        "events": "events",
    },
    ("todos", "todos.json"): {
        "todos": "todos",
    },
    ("agent-memory", "family_profile.json"): {
        "members": "family_profile",
    },
    ("agent-memory", "agent_state.json"): {
        "conversation_history": "agent_state",
    },
}

# Metadata fields stored as sheet-level named ranges or a separate meta row
_META_KEYS = {"version", "updated_at", "family_name", "preferences",
               "last_updated", "last_active_user", "last_agent_called"}


@lru_cache(maxsize=1)
def _get_client() -> gspread.Client:
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return gspread.Client(auth=creds)


@lru_cache(maxsize=1)
def _get_spreadsheet() -> gspread.Spreadsheet:
    return _get_client().open_by_key(settings.google_sheet_id)


def _get_or_create_worksheet(tab_name: str) -> gspread.Worksheet:
    """Return worksheet by name, creating it if it doesn't exist."""
    ss = _get_spreadsheet()
    try:
        return ss.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=tab_name, rows=1000, cols=20)
        return ws


def _rows_to_records(ws: gspread.Worksheet) -> list[dict]:
    """Read all rows from a worksheet into a list of dicts using the header row."""
    rows = ws.get_all_values()
    if not rows or len(rows) < 2:
        return []
    headers = rows[0]
    records = []
    for row in rows[1:]:
        # Pad short rows
        padded = row + [""] * (len(headers) - len(row))
        record = {}
        for header, value in zip(headers, padded):
            if not header:
                continue
            # Try to parse JSON-encoded values (lists, dicts)
            if value.startswith(("[", "{")):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass
            record[header] = value if value != "" else None
        records.append(record)
    return records


def _ensure_headers(ws: gspread.Worksheet, headers: list[str]) -> None:
    """Write headers to row 1 if not already set."""
    existing = ws.row_values(1)
    if existing != headers:
        ws.update("A1", [headers])


def _records_to_rows(records: list[dict], headers: list[str]) -> list[list]:
    rows = []
    for record in records:
        row = []
        for h in headers:
            val = record.get(h, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            row.append("" if val is None else str(val))
        rows.append(row)
    return rows


def store_read_json(folder: str, filename: str) -> dict:
    """Read all worksheet tabs for a logical file and return as a combined dict."""
    tab_map = _FILE_TAB_MAP.get((folder, filename), {})
    result: dict = {"version": "1.0", "updated_at": datetime.now(timezone.utc).isoformat()}

    for array_key, tab_name in tab_map.items():
        try:
            ws = _get_or_create_worksheet(tab_name)
            result[array_key] = _rows_to_records(ws)
        except Exception as exc:
            logger.warning("Could not read tab %s: %s", tab_name, exc)
            result[array_key] = []

    return result


def store_write_json(folder: str, filename: str, data: dict) -> None:
    """Write all array keys in data to their respective worksheet tabs."""
    tab_map = _FILE_TAB_MAP.get((folder, filename), {})

    for array_key, tab_name in tab_map.items():
        records = data.get(array_key, [])
        if not records:
            continue
        try:
            ws = _get_or_create_worksheet(tab_name)
            headers = list(records[0].keys())
            _ensure_headers(ws, headers)
            rows = _records_to_rows(records, headers)
            # Clear data rows (keep header), then write fresh
            ws.resize(rows=1)
            if rows:
                ws.append_rows(rows, value_input_option="RAW")
        except Exception as exc:
            logger.error("Failed to write tab %s: %s", tab_name, exc)


def store_append_record(folder: str, filename: str, record: dict, array_key: str) -> None:
    """Append a single record to the appropriate worksheet tab."""
    tab_map = _FILE_TAB_MAP.get((folder, filename), {})
    tab_name = tab_map.get(array_key)
    if not tab_name:
        logger.warning("No tab mapping for %s/%s[%s]", folder, filename, array_key)
        return

    try:
        ws = _get_or_create_worksheet(tab_name)
        headers = ws.row_values(1)

        if not headers:
            headers = list(record.keys())
            _ensure_headers(ws, headers)

        row = []
        for h in headers:
            val = record.get(h, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val)
            row.append("" if val is None else str(val))

        ws.append_row(row, value_input_option="RAW")
    except Exception as exc:
        logger.error("Failed to append to tab %s: %s", tab_name, exc)


def store_update_record(
    folder: str, filename: str, record_id: str, updates: dict, array_key: str
) -> bool:
    """Find a record by id and update its fields in the worksheet. Returns True if found."""
    tab_map = _FILE_TAB_MAP.get((folder, filename), {})
    tab_name = tab_map.get(array_key)
    if not tab_name:
        return False

    try:
        ws = _get_or_create_worksheet(tab_name)
        headers = ws.row_values(1)
        if not headers:
            return False

        id_col = headers.index("id") + 1  # 1-indexed
        id_cells = ws.col_values(id_col)

        for row_idx, cell_val in enumerate(id_cells[1:], start=2):  # skip header
            if cell_val == record_id:
                for key, val in updates.items():
                    if key in headers:
                        col_idx = headers.index(key) + 1
                        if isinstance(val, (list, dict)):
                            val = json.dumps(val)
                        ws.update_cell(row_idx, col_idx, str(val) if val is not None else "")
                return True
    except Exception as exc:
        logger.error("Failed to update record in tab %s: %s", tab_name, exc)

    return False


def store_delete_record(
    folder: str, filename: str, record_id: str, array_key: str
) -> bool:
    """Remove a record row from the worksheet by id. Returns True if found."""
    tab_map = _FILE_TAB_MAP.get((folder, filename), {})
    tab_name = tab_map.get(array_key)
    if not tab_name:
        return False

    try:
        ws = _get_or_create_worksheet(tab_name)
        headers = ws.row_values(1)
        if not headers or "id" not in headers:
            return False

        id_col = headers.index("id") + 1
        id_cells = ws.col_values(id_col)

        for row_idx, cell_val in enumerate(id_cells[1:], start=2):
            if cell_val == record_id:
                ws.delete_rows(row_idx)
                return True
    except Exception as exc:
        logger.error("Failed to delete record from tab %s: %s", tab_name, exc)

    return False
