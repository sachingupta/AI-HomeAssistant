"""
Data client facade — selects the storage backend based on DATA_STORE env var.

  DATA_STORE=sheets  →  Google Sheets (default; visible in browser for testing)
  DATA_STORE=drive   →  Google Drive JSON files (production)

All agents import from here — never directly from drive_client or sheets_client.
Switching backends requires only a .env change, no code changes.
"""

import logging
from backend.config import settings

logger = logging.getLogger(__name__)


def _load_backend():
    store = settings.data_store.strip().lower()
    if store == "drive":
        logger.info("Data backend: Google Drive JSON files")
        from backend import drive_client as _backend
    else:
        logger.info("Data backend: Google Sheets (id=%s)", settings.google_sheet_id)
        from backend import sheets_client as _backend
    return _backend


_backend = _load_backend()

drive_read_json = _backend.drive_read_json
drive_write_json = _backend.drive_write_json
drive_append_record = _backend.drive_append_record
drive_update_record = _backend.drive_update_record
drive_delete_record = _backend.drive_delete_record
