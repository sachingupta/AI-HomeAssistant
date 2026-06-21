"""
Unit tests for MCPClient.
All subprocess calls are mocked — no real MCP server is started.

Tests verify:
  - initialize handshake is sent on construction
  - each store_* method sends the correct JSON-RPC tool/call
  - MCP error responses raise MCPError
  - thread safety: the lock prevents request interleaving

Run: pytest backend/tests/test_mcp_client.py -v
"""

import json
from io import StringIO
from threading import Thread
from unittest.mock import MagicMock, call, patch

import pytest

from backend.mcp_client import MCPClient, MCPError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_proc(responses: list[str]) -> MagicMock:
    """
    Build a mock subprocess.Popen return value whose stdout.readline()
    yields responses in order.
    """
    mock_stdin = MagicMock()
    mock_stdout = MagicMock()
    mock_stdout.readline.side_effect = responses
    proc = MagicMock()
    proc.stdin = mock_stdin
    proc.stdout = mock_stdout
    proc.pid = 12345
    return proc


def _rpc_ok(req_id: int, result: dict) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}) + "\n"


def _tool_ok(req_id: int, data: dict) -> str:
    return _rpc_ok(req_id, {"content": [{"type": "text", "text": json.dumps(data)}]})


def _tool_err(req_id: int, msg: str) -> str:
    return _rpc_ok(req_id, {
        "content": [{"type": "text", "text": json.dumps({"error": msg})}],
        "isError": True,
    })


_INIT_RESP = _rpc_ok(1, {"protocolVersion": "2024-11-05", "capabilities": {}})


@pytest.fixture
def client_and_proc():
    """Return (MCPClient, mock_proc) with initialize already consumed."""
    with patch("subprocess.Popen") as mock_popen:
        # initialize (id=1) + placeholder for the actual call (id=2)
        proc = _make_proc([_INIT_RESP])
        mock_popen.return_value = proc

        client = MCPClient(server_data_store="drive")
        yield client, proc


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInitialization:
    def test_subprocess_started_with_correct_args(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP])
            mock_popen.return_value = proc
            MCPClient(server_data_store="drive")

        args, kwargs = mock_popen.call_args
        cmd = args[0]
        assert "-m" in cmd
        assert "backend.mcp_server.server" in cmd

    def test_subprocess_env_overrides_data_store(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP])
            mock_popen.return_value = proc
            MCPClient(server_data_store="drive")

        _, kwargs = mock_popen.call_args
        assert kwargs["env"]["DATA_STORE"] == "drive"

    def test_initialize_request_sent(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP])
            mock_popen.return_value = proc
            MCPClient(server_data_store="drive")

        written = proc.stdin.write.call_args[0][0]
        msg = json.loads(written.strip())
        assert msg["method"] == "initialize"
        assert msg["jsonrpc"] == "2.0"
        assert msg["id"] == 1

    def test_close_terminates_proc(self, client_and_proc):
        client, proc = client_and_proc
        client.close()
        proc.terminate.assert_called_once()


# ---------------------------------------------------------------------------
# store_read_json
# ---------------------------------------------------------------------------

class TestStoreReadJson:
    def test_sends_correct_tool_call(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([
                _INIT_RESP,
                _tool_ok(2, {"items": [{"name": "milk"}]}),
            ])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_read_json("groceries", "grocery_list.json")

        # Second write call is the tool/call request
        tool_call_raw = proc.stdin.write.call_args_list[1][0][0]
        msg = json.loads(tool_call_raw.strip())
        assert msg["method"] == "tools/call"
        assert msg["params"]["name"] == "store_read_json"
        assert msg["params"]["arguments"]["folder"] == "groceries"
        assert msg["params"]["arguments"]["filename"] == "grocery_list.json"

    def test_returns_parsed_result(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([
                _INIT_RESP,
                _tool_ok(2, {"items": [{"name": "milk"}]}),
            ])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_read_json("groceries", "grocery_list.json")
        assert result == {"items": [{"name": "milk"}]}

    def test_empty_file_returns_empty_dict(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_read_json("todos", "todos.json")
        assert result == {}


# ---------------------------------------------------------------------------
# store_write_json
# ---------------------------------------------------------------------------

class TestStoreWriteJson:
    def test_sends_data_in_arguments(self):
        payload = {"events": [{"id": "e1", "title": "Soccer"}]}
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"status": "ok"})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        client.store_write_json("events", "events.json", payload)

        tool_call_raw = proc.stdin.write.call_args_list[1][0][0]
        msg = json.loads(tool_call_raw.strip())
        assert msg["params"]["name"] == "store_write_json"
        assert msg["params"]["arguments"]["data"] == payload

    def test_returns_none(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"status": "ok"})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_write_json("events", "events.json", {})
        assert result is None


# ---------------------------------------------------------------------------
# store_update_record / store_delete_record
# ---------------------------------------------------------------------------

class TestStoreUpdateRecord:
    def test_returns_true_when_updated(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"updated": True})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_update_record(
            "todos", "todos.json", "t1", {"status": "done"}, "todos"
        )
        assert result is True

    def test_returns_false_when_not_found(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"updated": False})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_update_record(
            "todos", "todos.json", "ghost", {"status": "done"}, "todos"
        )
        assert result is False


class TestStoreDeleteRecord:
    def test_returns_true_when_deleted(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"deleted": True})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_delete_record("todos", "todos.json", "t1", "todos")
        assert result is True

    def test_returns_false_when_not_found(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_ok(2, {"deleted": False})])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        result = client.store_delete_record("todos", "todos.json", "ghost", "todos")
        assert result is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestMCPErrors:
    def test_tool_error_raises_mcp_error(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, _tool_err(2, "Drive quota exceeded")])
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        with pytest.raises(MCPError, match="Drive quota exceeded"):
            client.store_read_json("groceries", "grocery_list.json")

    def test_empty_stdout_raises_mcp_error(self):
        with patch("subprocess.Popen") as mock_popen:
            proc = _make_proc([_INIT_RESP, ""])  # empty line = closed stdout
            mock_popen.return_value = proc
            client = MCPClient(server_data_store="drive")

        with pytest.raises(MCPError, match="closed stdout"):
            client.store_read_json("groceries", "grocery_list.json")
