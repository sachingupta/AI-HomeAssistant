"""
Google Drive MCP Server for AI Home Assistant.

Implements the MCP protocol (JSON-RPC 2.0 over stdio) without the mcp SDK,
so it works on Python 3.9+ and teaches the raw protocol.

MCP wire format: one JSON object per line on stdout; reads from stdin.
  - Client sends:  {"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
  - Server sends:  {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}

Run standalone for testing:
    python -m backend.mcp_server.server
    # Then send JSON-RPC messages via stdin
"""

import json
import logging
import sys

from backend.data_client import (
    drive_append_record,
    drive_delete_record,
    drive_read_json,
    drive_update_record,
    drive_write_json,
)

logger = logging.getLogger(__name__)

_FOLDERS = ["events", "groceries", "todos", "agent-memory"]

_TOOLS = [
    {
        "name": "drive_read_json",
        "description": "Read and parse a JSON file from an AI Home Assistant Drive folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS, "description": "Subfolder name"},
                "filename": {"type": "string", "description": "JSON filename, e.g. grocery_list.json"},
            },
            "required": ["folder", "filename"],
        },
    },
    {
        "name": "drive_write_json",
        "description": "Write data as JSON to a Drive folder file (creates if missing).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS},
                "filename": {"type": "string"},
                "data": {"type": "object", "description": "Full JSON payload to write"},
            },
            "required": ["folder", "filename", "data"],
        },
    },
    {
        "name": "drive_append_record",
        "description": "Append a single record dict to a named JSON array inside a Drive file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS},
                "filename": {"type": "string"},
                "record": {"type": "object"},
                "array_key": {"type": "string", "description": "Top-level key of the array, e.g. 'items'"},
            },
            "required": ["folder", "filename", "record", "array_key"],
        },
    },
    {
        "name": "drive_update_record",
        "description": "Find a record by its 'id' field and patch specified fields in place.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS},
                "filename": {"type": "string"},
                "record_id": {"type": "string"},
                "updates": {"type": "object"},
                "array_key": {"type": "string"},
            },
            "required": ["folder", "filename", "record_id", "updates", "array_key"],
        },
    },
    {
        "name": "drive_delete_record",
        "description": "Remove a record from a JSON array by its 'id' field.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS},
                "filename": {"type": "string"},
                "record_id": {"type": "string"},
                "array_key": {"type": "string"},
            },
            "required": ["folder", "filename", "record_id", "array_key"],
        },
    },
    {
        "name": "drive_list_files",
        "description": "List all known JSON filenames in an AI Home Assistant subfolder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": _FOLDERS},
            },
            "required": ["folder"],
        },
    },
]


def _send(obj: dict) -> None:
    """Write one JSON-RPC message to stdout."""
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _respond(request_id, result: dict) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def _dispatch(name: str, args: dict) -> dict:
    """Execute an MCP tool and return the result dict."""
    if name == "drive_read_json":
        return drive_read_json(args["folder"], args["filename"])

    if name == "drive_write_json":
        drive_write_json(args["folder"], args["filename"], args["data"])
        return {"status": "ok"}

    if name == "drive_append_record":
        drive_append_record(
            args["folder"], args["filename"],
            args["record"], args["array_key"],
        )
        return {"status": "ok"}

    if name == "drive_update_record":
        updated = drive_update_record(
            args["folder"], args["filename"],
            args["record_id"], args["updates"], args["array_key"],
        )
        return {"updated": updated}

    if name == "drive_delete_record":
        deleted = drive_delete_record(
            args["folder"], args["filename"],
            args["record_id"], args["array_key"],
        )
        return {"deleted": deleted}

    if name == "drive_list_files":
        from backend.sheets_client import _FILE_TAB_MAP
        files = [fn for (fld, fn) in _FILE_TAB_MAP if fld == args["folder"]]
        return {"folder": args["folder"], "files": files}

    raise ValueError(f"Unknown tool: {name}")


def _handle(request: dict) -> None:
    """Process one JSON-RPC request and write response to stdout."""
    method = request.get("method", "")
    req_id = request.get("id")          # None for notifications
    params = request.get("params") or {}

    # Notifications have no id and require no response
    if req_id is None:
        return

    if method == "initialize":
        _respond(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ai-home-assistant-google-drive", "version": "1.0.0"},
        })

    elif method == "tools/list":
        _respond(req_id, {"tools": _TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result = _dispatch(tool_name, arguments)
            _respond(req_id, {
                "content": [{"type": "text", "text": json.dumps(result)}]
            })
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_name, exc)
            _respond(req_id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                "isError": True,
            })

    else:
        _error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    """Read newline-delimited JSON-RPC messages from stdin and respond on stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": f"Parse error: {exc}"}})
            continue
        _handle(request)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    main()
