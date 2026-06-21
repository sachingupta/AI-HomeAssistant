"""
Events Agent tool implementations.
Each function is also registered as a Claude tool in agent.py.
All storage access goes through data_client — backend-agnostic.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import dateparser

from backend.data_client import store_read_json, store_write_json
from backend.agents.events.schemas import Event, EventStore

_FOLDER = "events"
_FILE = "events.json"


def _load_store() -> EventStore:
    data = store_read_json(_FOLDER, _FILE)
    if not data:
        return EventStore()
    return EventStore.model_validate(data)


def _save_store(store: EventStore) -> None:
    store.updated_at = datetime.now(timezone.utc).isoformat()
    store_write_json(_FOLDER, _FILE, store.model_dump(mode="json"))


def _parse_dt(datetime_str: str) -> datetime:
    """Parse a natural-language or ISO datetime string into a datetime object."""
    parsed = dateparser.parse(
        datetime_str,
        settings={"RETURN_AS_TIMEZONE_AWARE": False, "PREFER_DATES_FROM": "future"},
    )
    if parsed is None:
        raise ValueError(f"Could not parse datetime: {datetime_str!r}")
    return parsed


def add_event(
    title: str,
    datetime_str: str,
    duration_minutes: int = 60,
    location: str = "",
    participants: list = None,
    driver: str = "",
    notes: str = "",
    recurring: dict = None,
) -> dict:
    """Add a new event to the family calendar.

    Args:
        title: Title or name of the event.
        datetime_str: When the event starts (ISO string or natural language like "Saturday 10am").
        duration_minutes: How long the event lasts in minutes (default 60).
        location: Where the event takes place.
        participants: List of family member names attending.
        driver: Who is driving/responsible for transport.
        notes: Any additional notes.
        recurring: Optional dict with 'frequency' and 'until' keys for recurring events.

    Returns:
        dict with 'added' key containing the saved event dict.
    """
    if participants is None:
        participants = []

    parsed = _parse_dt(datetime_str)
    iso_str = parsed.isoformat()

    event = Event(
        title=title,
        **{"datetime": iso_str},
        duration_minutes=duration_minutes,
        location=location,
        participants=participants,
        driver=driver,
        notes=notes,
        recurring=recurring,
    )

    store = _load_store()
    store.events.append(event.model_dump(mode="json", by_alias=True))
    _save_store(store)

    return {"added": event.model_dump(mode="json", by_alias=True)}


def get_events(start_date: str = "", end_date: str = "", person: str = "") -> dict:
    """Retrieve events from the calendar with optional filters.

    Args:
        start_date: Filter events on or after this date (ISO date string, e.g. "2026-06-21").
        end_date: Filter events on or before this date (ISO date string, e.g. "2026-06-28").
        person: Filter events where this person is in participants.

    Returns:
        dict with 'events' list and 'total' count.
    """
    store = _load_store()
    events = store.events

    filtered = []
    for ev in events:
        dt_str = ev.get("datetime", "")
        try:
            ev_dt = datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            continue

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                if ev_dt < start_dt:
                    continue
            except ValueError:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                if end_dt.hour == 0 and end_dt.minute == 0 and end_dt.second == 0:
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                if ev_dt > end_dt:
                    continue
            except ValueError:
                pass

        if person:
            participants = ev.get("participants", [])
            if person.lower() not in [p.lower() for p in participants]:
                continue

        filtered.append(ev)

    filtered.sort(key=lambda e: e.get("datetime", ""))
    return {"events": filtered, "total": len(filtered)}


def get_weekly_digest() -> dict:
    """Return upcoming events grouped by day for the next 7 days.

    Returns:
        dict with 'week_start', 'week_end', 'by_day' (date string → list of events), and 'total'.
    """
    now = datetime.now()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    store = _load_store()
    by_day: dict = {}
    total = 0

    for ev in store.events:
        dt_str = ev.get("datetime", "")
        try:
            ev_dt = datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            continue

        if week_start <= ev_dt < week_end:
            day_key = ev_dt.strftime("%Y-%m-%d")
            by_day.setdefault(day_key, [])
            by_day[day_key].append(ev)
            total += 1

    for day_key in by_day:
        by_day[day_key].sort(key=lambda e: e.get("datetime", ""))

    return {
        "week_start": week_start.date().isoformat(),
        "week_end": week_end.date().isoformat(),
        "by_day": by_day,
        "total": total,
    }


def check_conflicts(datetime_str: str, duration_minutes: int = 60) -> dict:
    """Check whether a proposed event time overlaps with existing events.

    Args:
        datetime_str: Proposed start time (ISO or natural language).
        duration_minutes: Duration of the proposed event in minutes.

    Returns:
        dict with 'has_conflict' bool and 'conflicts' list of conflicting event summaries.
    """
    new_start = _parse_dt(datetime_str)
    new_end = new_start + timedelta(minutes=duration_minutes)

    store = _load_store()
    conflicts = []

    for ev in store.events:
        dt_str = ev.get("datetime", "")
        try:
            ev_start = datetime.fromisoformat(dt_str)
        except (ValueError, TypeError):
            continue

        ev_duration = ev.get("duration_minutes", 60)
        ev_end = ev_start + timedelta(minutes=ev_duration)

        if ev_start < new_end and ev_end > new_start:
            conflicts.append({
                "title": ev.get("title", ""),
                "datetime": dt_str,
                "duration_minutes": ev_duration,
            })

    return {"has_conflict": len(conflicts) > 0, "conflicts": conflicts}


def update_event(event_id: str, updates: dict) -> dict:
    """Update fields of an existing event by its ID.

    Args:
        event_id: The unique ID of the event to update.
        updates: Dict of field names and new values to apply.

    Returns:
        dict with 'updated' bool indicating success.
    """
    store = _load_store()

    for i, ev in enumerate(store.events):
        if ev.get("id") == event_id:
            store.events[i].update(updates)
            _save_store(store)
            return {"updated": True}

    return {"updated": False}


def delete_event(event_id: str) -> dict:
    """Delete an event from the calendar by its ID.

    Args:
        event_id: The unique ID of the event to delete.

    Returns:
        dict with 'deleted' bool indicating success.
    """
    store = _load_store()
    original_count = len(store.events)
    store.events = [ev for ev in store.events if ev.get("id") != event_id]

    if len(store.events) < original_count:
        _save_store(store)
        return {"deleted": True}

    return {"deleted": False}


# Tool definitions for the Claude API
EVENTS_TOOLS = [
    {
        "name": "add_event",
        "description": (
            "Add a new event to the family calendar. "
            "Always call check_conflicts before adding to avoid scheduling conflicts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Title or name of the event"},
                "datetime_str": {
                    "type": "string",
                    "description": "Start time (ISO string or natural language like 'Saturday 10am')",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes (default 60)",
                },
                "location": {"type": "string", "description": "Where the event takes place"},
                "participants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Family members attending",
                },
                "driver": {"type": "string", "description": "Who is driving"},
                "notes": {"type": "string", "description": "Additional notes"},
                "recurring": {
                    "type": "object",
                    "description": "Recurrence rule with 'frequency' and 'until' (ISO date)",
                    "properties": {
                        "frequency": {"type": "string"},
                        "until": {"type": "string"},
                    },
                },
            },
            "required": ["title", "datetime_str"],
        },
    },
    {
        "name": "get_events",
        "description": "Retrieve calendar events with optional date range and person filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Filter events on or after this ISO date (e.g. '2026-06-21')",
                },
                "end_date": {
                    "type": "string",
                    "description": "Filter events on or before this ISO date",
                },
                "person": {
                    "type": "string",
                    "description": "Filter events where this person is a participant",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_weekly_digest",
        "description": "Get all events in the next 7 days, grouped by day for easy reading.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "check_conflicts",
        "description": "Check if a proposed event time overlaps with existing calendar events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "datetime_str": {
                    "type": "string",
                    "description": "Proposed start time (ISO or natural language)",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration of the proposed event in minutes (default 60)",
                },
            },
            "required": ["datetime_str"],
        },
    },
    {
        "name": "update_event",
        "description": "Update one or more fields of an existing event by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID of the event to update"},
                "updates": {
                    "type": "object",
                    "description": "Fields to update (e.g. {'title': 'New Title', 'location': 'Park'})",
                },
            },
            "required": ["event_id", "updates"],
        },
    },
    {
        "name": "delete_event",
        "description": "Permanently delete an event from the calendar by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "ID of the event to delete"},
            },
            "required": ["event_id"],
        },
    },
]

# Map tool name → function for the ReAct executor
TOOL_REGISTRY = {
    "add_event": add_event,
    "get_events": get_events,
    "get_weekly_digest": get_weekly_digest,
    "check_conflicts": check_conflicts,
    "update_event": update_event,
    "delete_event": delete_event,
}
