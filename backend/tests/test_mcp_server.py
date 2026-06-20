"""
Unit tests for the MCP server tool dispatch layer.
Tests _dispatch() directly — no MCP transport, no real Google credentials.
"""

from unittest.mock import patch

import pytest

_MOCK_STORE: dict = {}


def _mock_read(folder, filename):
    return _MOCK_STORE.get(f"{folder}/{filename}", {})


def _mock_write(folder, filename, data):
    _MOCK_STORE[f"{folder}/{filename}"] = data


def _mock_append(folder, filename, record, array_key):
    key = f"{folder}/{filename}"
    obj = _MOCK_STORE.setdefault(key, {array_key: []})
    obj.setdefault(array_key, []).append(record)


def _mock_update(folder, filename, record_id, updates, array_key):
    key = f"{folder}/{filename}"
    for rec in _MOCK_STORE.get(key, {}).get(array_key, []):
        if rec.get("id") == record_id:
            rec.update(updates)
            return True
    return False


def _mock_delete(folder, filename, record_id, array_key):
    key = f"{folder}/{filename}"
    arr = _MOCK_STORE.get(key, {}).get(array_key, [])
    original = len(arr)
    arr[:] = [r for r in arr if r.get("id") != record_id]
    return len(arr) < original


@pytest.fixture(autouse=True)
def reset_store():
    _MOCK_STORE.clear()
    yield
    _MOCK_STORE.clear()


@pytest.fixture(autouse=True)
def patch_data_client(reset_store):
    with (
        patch("backend.mcp_server.server.drive_read_json", side_effect=_mock_read),
        patch("backend.mcp_server.server.drive_write_json", side_effect=_mock_write),
        patch("backend.mcp_server.server.drive_append_record", side_effect=_mock_append),
        patch("backend.mcp_server.server.drive_update_record", side_effect=_mock_update),
        patch("backend.mcp_server.server.drive_delete_record", side_effect=_mock_delete),
    ):
        yield


from backend.mcp_server.server import _dispatch


class TestDriveReadJson:
    def test_returns_empty_dict_when_missing(self):
        result = _dispatch("drive_read_json", {"folder": "groceries", "filename": "grocery_list.json"})
        assert result == {}

    def test_returns_stored_data(self):
        _MOCK_STORE["groceries/grocery_list.json"] = {"items": [{"name": "milk"}]}
        result = _dispatch("drive_read_json", {"folder": "groceries", "filename": "grocery_list.json"})
        assert result["items"][0]["name"] == "milk"


class TestDriveWriteJson:
    def test_write_returns_ok(self):
        result = _dispatch("drive_write_json", {
            "folder": "todos", "filename": "todos.json", "data": {"todos": []}
        })
        assert result == {"status": "ok"}

    def test_data_is_persisted(self):
        _dispatch("drive_write_json", {
            "folder": "todos", "filename": "todos.json", "data": {"todos": [{"id": "1"}]}
        })
        assert _MOCK_STORE["todos/todos.json"]["todos"][0]["id"] == "1"


class TestDriveAppendRecord:
    def test_append_adds_record(self):
        result = _dispatch("drive_append_record", {
            "folder": "events", "filename": "events.json",
            "record": {"id": "abc", "title": "Soccer"},
            "array_key": "events",
        })
        assert result == {"status": "ok"}
        assert _MOCK_STORE["events/events.json"]["events"][0]["title"] == "Soccer"

    def test_multiple_appends(self):
        for i in range(3):
            _dispatch("drive_append_record", {
                "folder": "events", "filename": "events.json",
                "record": {"id": str(i), "title": f"Event {i}"},
                "array_key": "events",
            })
        assert len(_MOCK_STORE["events/events.json"]["events"]) == 3


class TestDriveUpdateRecord:
    def test_update_existing_record(self):
        _MOCK_STORE["todos/todos.json"] = {"todos": [{"id": "t1", "status": "pending"}]}
        result = _dispatch("drive_update_record", {
            "folder": "todos", "filename": "todos.json",
            "record_id": "t1", "updates": {"status": "done"}, "array_key": "todos",
        })
        assert result == {"updated": True}
        assert _MOCK_STORE["todos/todos.json"]["todos"][0]["status"] == "done"

    def test_update_nonexistent_record(self):
        result = _dispatch("drive_update_record", {
            "folder": "todos", "filename": "todos.json",
            "record_id": "ghost", "updates": {"status": "done"}, "array_key": "todos",
        })
        assert result == {"updated": False}


class TestDriveDeleteRecord:
    def test_delete_existing_record(self):
        _MOCK_STORE["todos/todos.json"] = {"todos": [{"id": "t1"}, {"id": "t2"}]}
        result = _dispatch("drive_delete_record", {
            "folder": "todos", "filename": "todos.json",
            "record_id": "t1", "array_key": "todos",
        })
        assert result == {"deleted": True}
        assert len(_MOCK_STORE["todos/todos.json"]["todos"]) == 1

    def test_delete_nonexistent_record(self):
        result = _dispatch("drive_delete_record", {
            "folder": "todos", "filename": "todos.json",
            "record_id": "ghost", "array_key": "todos",
        })
        assert result == {"deleted": False}


class TestUnknownTool:
    def test_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            _dispatch("drive_explode", {})
