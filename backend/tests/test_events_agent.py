"""
Unit tests for Events Agent tools.
These tests mock the store client so no real Google credentials are needed.
Run: pytest backend/tests/test_events_agent.py -v
"""

from unittest.mock import patch

import pytest

_MOCK_STORE: dict = {}


def _mock_read(folder, filename):
    return _MOCK_STORE.get(f"{folder}/{filename}", {})


def _mock_write(folder, filename, data):
    _MOCK_STORE[f"{folder}/{filename}"] = data


@pytest.fixture(autouse=True)
def reset_store():
    _MOCK_STORE.clear()
    yield
    _MOCK_STORE.clear()


@pytest.fixture(autouse=True)
def patch_drive(reset_store):
    with (
        patch("backend.agents.events.tools.store_read_json", side_effect=_mock_read),
        patch("backend.agents.events.tools.store_write_json", side_effect=_mock_write),
    ):
        yield


from backend.agents.events.tools import (  # noqa: E402
    add_event,
    check_conflicts,
    delete_event,
    get_events,
    get_weekly_digest,
    update_event,
)


def _add_fixed_event(
    title: str,
    datetime_iso: str,
    duration_minutes: int = 60,
    participants: list = None,
    **kwargs,
) -> dict:
    """Write an event directly to the mock store with a fixed ISO datetime (no dateparser)."""
    from backend.agents.events.schemas import EventStore
    import uuid

    store_data = _MOCK_STORE.get("events/events.json", {})
    store = EventStore.model_validate(store_data) if store_data else EventStore()

    event_dict = {
        "id": uuid.uuid4().hex,
        "datetime": datetime_iso,
        "title": title,
        "duration_minutes": duration_minutes,
        "location": kwargs.get("location", ""),
        "participants": participants or [],
        "driver": kwargs.get("driver", ""),
        "recurring": kwargs.get("recurring"),
        "notes": kwargs.get("notes", ""),
        "created_at": "2026-06-20T00:00:00Z",
    }
    store.events.append(event_dict)
    _MOCK_STORE["events/events.json"] = store.model_dump(mode="json")
    return event_dict


class TestAddEvent:
    def test_add_event_returns_added_dict(self):
        result = add_event(title="Doctor", datetime_str="2026-06-25T10:00:00")
        assert "added" in result
        assert result["added"]["title"] == "Doctor"
        assert "id" in result["added"]

    def test_added_event_appears_in_store(self):
        add_event(title="Soccer practice", datetime_str="2026-06-26T15:00:00")
        result = get_events()
        assert result["total"] == 1
        assert result["events"][0]["title"] == "Soccer practice"

    def test_add_event_with_location_and_participants(self):
        result = add_event(
            title="Birthday party",
            datetime_str="2026-06-28T14:00:00",
            location="Community Center",
            participants=["Alice", "Bob"],
        )
        added = result["added"]
        assert added["location"] == "Community Center"
        assert "Alice" in added["participants"]
        assert "Bob" in added["participants"]


class TestGetEvents:
    def test_get_all_events_no_filter(self):
        _add_fixed_event("Event A", "2026-06-21T09:00:00")
        _add_fixed_event("Event B", "2026-06-22T10:00:00")
        result = get_events()
        assert result["total"] == 2

    def test_filter_by_person(self):
        _add_fixed_event("Alice's recital", "2026-06-21T18:00:00", participants=["Alice"])
        _add_fixed_event("Bob's game", "2026-06-22T10:00:00", participants=["Bob"])
        result = get_events(person="Alice")
        assert result["total"] == 1
        assert result["events"][0]["title"] == "Alice's recital"

    def test_filter_by_date_range(self):
        _add_fixed_event("Early event", "2026-06-21T08:00:00")
        _add_fixed_event("Late event", "2026-06-28T08:00:00")
        result = get_events(start_date="2026-06-27", end_date="2026-06-29")
        assert result["total"] == 1
        assert result["events"][0]["title"] == "Late event"


class TestGetWeeklyDigest:
    def test_digest_returns_by_day_structure(self):
        from datetime import datetime, timedelta
        soon = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%dT10:00:00")
        _add_fixed_event("Upcoming event", soon)
        result = get_weekly_digest()
        assert "by_day" in result
        assert "week_start" in result
        assert "week_end" in result
        assert result["total"] == 1
        assert len(result["by_day"]) == 1

    def test_digest_excludes_past_events(self):
        _add_fixed_event("Past event", "2020-01-01T10:00:00")
        result = get_weekly_digest()
        assert result["total"] == 0
        assert result["by_day"] == {}


class TestCheckConflicts:
    def test_detects_overlapping_event(self):
        _add_fixed_event("Morning meeting", "2026-06-25T10:00:00", duration_minutes=60)
        result = check_conflicts("2026-06-25T10:30:00", duration_minutes=60)
        assert result["has_conflict"] is True
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["title"] == "Morning meeting"

    def test_no_conflict_when_sequential(self):
        _add_fixed_event("Early meeting", "2026-06-25T09:00:00", duration_minutes=60)
        result = check_conflicts("2026-06-25T10:00:00", duration_minutes=60)
        assert result["has_conflict"] is False
        assert result["conflicts"] == []

    def test_no_conflict_on_empty_store(self):
        result = check_conflicts("2026-06-25T10:00:00", duration_minutes=60)
        assert result["has_conflict"] is False
        assert result["conflicts"] == []


class TestUpdateEvent:
    def test_update_existing_event(self):
        ev = _add_fixed_event("Team lunch", "2026-06-24T12:00:00")
        result = update_event(ev["id"], {"title": "Team dinner", "location": "Italian place"})
        assert result["updated"] is True
        events = get_events()
        updated = events["events"][0]
        assert updated["title"] == "Team dinner"
        assert updated["location"] == "Italian place"

    def test_update_nonexistent_event(self):
        result = update_event("nonexistent-id-000", {"title": "Ghost event"})
        assert result["updated"] is False


class TestDeleteEvent:
    def test_delete_existing_event(self):
        ev = _add_fixed_event("Dentist appointment", "2026-06-27T09:00:00")
        result = delete_event(ev["id"])
        assert result["deleted"] is True
        assert get_events()["total"] == 0

    def test_delete_nonexistent_event(self):
        result = delete_event("nonexistent-id-999")
        assert result["deleted"] is False
