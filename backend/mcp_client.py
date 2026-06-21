"""
MCP Client — manages the MCP server subprocess and proxies all storage
operations to it via JSON-RPC 2.0 over stdin/stdout.

When DATA_STORE=mcp, data_client.py uses this instead of calling
drive_client or sheets_client directly.  The subprocess itself is started
with DATA_STORE forced to a real backend (drive or sheets) so there is
no infinite recursion.

Wire format (one JSON object per newline):
  → {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{...}}
  ← {"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"..."}]}}
"""

import json
import logging
import os
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)


class MCPError(RuntimeError):
    """Raised when the MCP server returns an error response."""


class MCPClient:
    """
    Spawns backend/mcp_server/server.py as a subprocess and communicates
    via newline-delimited JSON-RPC 2.0 over stdin/stdout.

    Thread-safe: a lock serialises every request/response pair so concurrent
    agent calls don't interleave on the pipe.

    Args:
        server_data_store: DATA_STORE value for the subprocess.  Defaults to
            "drive" — the MCP server always needs a *real* storage backend;
            never pass "mcp" here or you'll get a subprocess loop.
    """

    def __init__(self, server_data_store: str = "drive"):
        self._lock = threading.Lock()
        self._request_id = 0
        self._proc: subprocess.Popen | None = None
        self._server_data_store = server_data_store
        self._start()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start(self) -> None:
        env = os.environ.copy()
        env["DATA_STORE"] = self._server_data_store   # never "mcp"

        self._proc = subprocess.Popen(
            [sys.executable, "-m", "backend.mcp_server.server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,           # line-buffered
            env=env,
        )
        logger.info("MCP server subprocess started (pid=%s)", self._proc.pid)

        # MCP initialize handshake — required before any tool/call
        result = self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ai-home-assistant-backend", "version": "1.0.0"},
        })
        logger.info("MCP server ready — protocolVersion=%s", result.get("protocolVersion"))

    def close(self) -> None:
        """Terminate the MCP server subprocess."""
        if self._proc:
            try:
                self._proc.stdin.close()
            except OSError:
                pass
            self._proc.terminate()
            self._proc = None

    # ------------------------------------------------------------------
    # JSON-RPC transport
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _rpc(self, method: str, params: dict) -> dict:
        """Send one JSON-RPC request and return the result dict."""
        assert self._proc is not None, "MCP server is not running"
        req_id = self._next_id()
        msg = json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})

        self._proc.stdin.write(msg + "\n")
        self._proc.stdin.flush()

        raw = self._proc.stdout.readline()
        if not raw:
            raise MCPError("MCP server closed stdout unexpectedly")

        resp = json.loads(raw)
        if "error" in resp:
            raise MCPError(f"MCP error {resp['error']['code']}: {resp['error']['message']}")
        return resp.get("result", {})

    def _tool_call(self, name: str, arguments: dict) -> dict:
        """Call a named MCP tool and return the parsed result dict."""
        with self._lock:
            result = self._rpc("tools/call", {"name": name, "arguments": arguments})

        # MCP wraps tool results in a content array
        content = result.get("content", [{}])
        text = content[0].get("text", "{}")
        data = json.loads(text)

        if result.get("isError") or "error" in data:
            raise MCPError(f"Tool '{name}' returned error: {data.get('error', 'unknown')}")
        return data

    # ------------------------------------------------------------------
    # Store operations — same signatures as drive_client / sheets_client
    # ------------------------------------------------------------------

    def store_read_json(self, folder: str, filename: str) -> dict:
        return self._tool_call("store_read_json", {"folder": folder, "filename": filename})

    def store_write_json(self, folder: str, filename: str, data: dict) -> None:
        self._tool_call("store_write_json", {"folder": folder, "filename": filename, "data": data})

    def store_append_record(
        self, folder: str, filename: str, record: dict, array_key: str
    ) -> None:
        self._tool_call("store_append_record", {
            "folder": folder, "filename": filename,
            "record": record, "array_key": array_key,
        })

    def store_update_record(
        self, folder: str, filename: str,
        record_id: str, updates: dict, array_key: str,
    ) -> bool:
        result = self._tool_call("store_update_record", {
            "folder": folder, "filename": filename,
            "record_id": record_id, "updates": updates, "array_key": array_key,
        })
        return bool(result.get("updated", False))

    def store_delete_record(
        self, folder: str, filename: str,
        record_id: str, array_key: str,
    ) -> bool:
        result = self._tool_call("store_delete_record", {
            "folder": folder, "filename": filename,
            "record_id": record_id, "array_key": array_key,
        })
        return bool(result.get("deleted", False))
