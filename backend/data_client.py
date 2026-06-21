"""
Data client facade — selects the storage backend based on DATA_STORE env var.

  DATA_STORE=sheets  →  Google Sheets (default; visible in browser for testing)
  DATA_STORE=drive   →  Google Drive JSON files (production)
  DATA_STORE=mcp     →  MCP server subprocess (JSON-RPC 2.0 over stdio)
                         The MCP server itself uses DATA_STORE=drive.
                         Use this to observe all storage calls in the MCP trace.

All agents import from here — never directly from any backend module.
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
        return _backend
    if store == "mcp":
        logger.info("Data backend: MCP server subprocess (real backend=drive)")
        from backend.mcp_client import MCPClient
        return MCPClient(server_data_store="drive")
    # default: sheets
    logger.info("Data backend: Google Sheets (id=%s)", settings.google_sheet_id)
    from backend import sheets_client as _backend
    return _backend


_backend = _load_backend()

store_read_json = _backend.store_read_json
store_write_json = _backend.store_write_json
store_append_record = _backend.store_append_record
store_update_record = _backend.store_update_record
store_delete_record = _backend.store_delete_record
