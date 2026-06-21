"""
Intent classifier for the Orchestrator.
Fast keyword-based routing with a General fallback for ambiguous inputs.
"""

from enum import Enum


class Intent(str, Enum):
    grocery = "grocery"
    events = "events"
    todos = "todos"
    digest = "digest"    # multi-agent weekly summary
    general = "general"  # greetings, questions about the system, etc.


_GROCERY = [
    "grocery", "groceries", "shopping", "shop", "supermarket", "store",
    "buy", "bought", "purchase", "purchased", "fridge", "pantry", "ingredient",
    "milk", "eggs", "bread", "butter", "cheese", "meat", "chicken", "beef",
    "produce", "fruit", "vegetable", "snack", "drink", "juice", "coffee",
    "add to list", "out of", "need more", "running low", "pick up",
]

_EVENTS = [
    "event", "calendar", "schedule", "appointment", "practice", "game",
    "recital", "meeting", "birthday", "party", "concert", "dentist", "doctor",
    "school", "pickup", "drop off", "drive", "conflict", "overlap",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "today", "tomorrow", "next week", "this weekend",
    " am", " pm", "o'clock", ":00", ":30",
]

_TODOS = [
    "todo", "task", "chore", "remind", "reminder", "errand",
    "fix", "clean", "repair", "mow", "laundry", "dishes", "vacuum",
    "assign", "delegate", "complete", "finish", "done", "pending", "overdue",
    "due", "by friday", "by saturday", "by sunday", "homework",
]

_DIGEST = [
    "week", "weekly", "summary", "digest", "overview", "happening",
    "going on", "what's up", "catch up", "everything", "all of it",
    "what do we have", "what's on", "plan for", "look like",
]


def classify(message: str) -> Intent:
    """Classify a user message into one of the routing intents.

    Uses keyword scoring. Digest wins if multiple digest signals are present.
    Returns Intent.general when no domain keywords match.
    """
    msg = message.lower()

    # Digest: needs at least 2 digest signals to avoid false positives
    digest_hits = sum(1 for kw in _DIGEST if kw in msg)
    if digest_hits >= 2:
        return Intent.digest

    scores = {
        Intent.grocery: sum(1 for kw in _GROCERY if kw in msg),
        Intent.events:  sum(1 for kw in _EVENTS if kw in msg),
        Intent.todos:   sum(1 for kw in _TODOS if kw in msg),
    }

    best, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score > 0:
        return best

    return Intent.general
