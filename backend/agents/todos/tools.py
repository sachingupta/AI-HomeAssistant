"""
Todos Agent tool implementations.
Each function is also registered as a Claude tool in agent.py.
All storage access goes through data_client — swap DATA_STORE env var to switch backends.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional

from backend.data_client import store_read_json, store_write_json
from backend.agents.todos.schemas import Todo, TodoStatus, Priority, TodoStore

_FOLDER = "todos"
_FILE = "todos.json"

_PRIORITY_ORDER = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}


def _load_store() -> TodoStore:
    data = store_read_json(_FOLDER, _FILE)
    if not data:
        return TodoStore()
    return TodoStore.model_validate(data)


def _save_store(store: TodoStore) -> None:
    store.updated_at = datetime.now(timezone.utc).isoformat()
    store_write_json(_FOLDER, _FILE, store.model_dump(mode="json"))


def add_todo(
    title: str,
    description: str = "",
    assignee: str = "",
    created_by: str = "unknown",
    due_date: str = "",
    priority: str = "medium",
    tags: Optional[List] = None,
) -> dict:
    """Add a new todo item to the family task list.

    Args:
        title: Short title of the task.
        description: Longer description or details about the task.
        assignee: Family member responsible for the task.
        created_by: Family member who created the task.
        due_date: Due date in YYYY-MM-DD format (optional).
        priority: Task priority — low, medium, or high.
        tags: List of tag strings for categorization.

    Returns:
        dict with 'added' key containing the new todo as a dict.
    """
    store = _load_store()
    todo = Todo(
        title=title,
        description=description,
        assignee=assignee,
        created_by=created_by,
        due_date=due_date if due_date else None,
        priority=Priority(priority) if priority else Priority.medium,
        tags=tags if tags is not None else [],
    )
    store.todos.append(todo)
    _save_store(store)
    return {"added": todo.model_dump(mode="json")}


def get_todos(
    assignee: str = "",
    status: str = "",
    priority: str = "",
) -> dict:
    """Return todos, optionally filtered by assignee, status, and/or priority.

    If no filters are provided, returns all non-cancelled todos sorted by due_date
    (nulls last), then by priority (high > medium > low).

    Args:
        assignee: Filter to a specific family member (case-insensitive).
        status: Filter by status — pending, in_progress, done, or cancelled.
        priority: Filter by priority — low, medium, or high.

    Returns:
        dict with 'todos' list and 'total' count.
    """
    store = _load_store()
    todos = store.todos

    if not assignee and not status and not priority:
        todos = [t for t in todos if t.status != TodoStatus.cancelled]
    else:
        if assignee:
            todos = [t for t in todos if t.assignee.lower() == assignee.lower()]
        if status:
            todos = [t for t in todos if t.status.value == status]
        if priority:
            todos = [t for t in todos if t.priority.value == priority]

    def sort_key(t: Todo):
        date_key = t.due_date if t.due_date else "9999-99-99"
        prio_key = _PRIORITY_ORDER.get(t.priority, 1)
        return (date_key, prio_key)

    todos = sorted(todos, key=sort_key)
    return {"todos": [t.model_dump(mode="json") for t in todos], "total": len(todos)}


def complete_todo(todo_id: str, completed_by: str = "unknown") -> dict:
    """Mark a todo as done and record who completed it.

    Args:
        todo_id: The hex ID of the todo to complete.
        completed_by: Family member who completed the task.

    Returns:
        dict with 'completed' bool and 'title' of the todo if found.
    """
    store = _load_store()
    for todo in store.todos:
        if todo.id == todo_id:
            todo.status = TodoStatus.done
            todo.completed_by = completed_by
            todo.completed_at = datetime.now(timezone.utc).isoformat()
            _save_store(store)
            return {"completed": True, "title": todo.title}
    return {"completed": False, "title": None}


def assign_todo(todo_id: str, assignee: str) -> dict:
    """Assign a todo to a specific family member.

    Args:
        todo_id: The hex ID of the todo to assign.
        assignee: Name of the family member to assign the task to.

    Returns:
        dict with 'assigned' bool indicating whether the assignment was successful.
    """
    store = _load_store()
    for todo in store.todos:
        if todo.id == todo_id:
            todo.assignee = assignee
            _save_store(store)
            return {"assigned": True}
    return {"assigned": False}


def get_weekly_summary() -> dict:
    """Return a summary of todos for the current week.

    Counts todos by status for items created or due within the last 7 days.
    Overdue means due_date is before today and status is not done or cancelled.

    Returns:
        dict with counts per status (pending, in_progress, done, cancelled, overdue)
        and a 'todos' list of pending/in_progress items sorted by due_date.
    """
    store = _load_store()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    week_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    counts = {"pending": 0, "in_progress": 0, "done": 0, "cancelled": 0, "overdue": 0}
    active_todos = []

    for todo in store.todos:
        in_window = False
        if todo.created_at and todo.created_at[:10] >= week_ago_str:
            in_window = True
        if todo.due_date and todo.due_date >= week_ago_str:
            in_window = True

        if not in_window:
            continue

        status_val = todo.status.value
        if status_val in counts:
            counts[status_val] += 1

        if (
            todo.due_date
            and todo.due_date < today_str
            and todo.status not in (TodoStatus.done, TodoStatus.cancelled)
        ):
            counts["overdue"] += 1

        if todo.status in (TodoStatus.pending, TodoStatus.in_progress):
            active_todos.append(todo)

    active_todos = sorted(active_todos, key=lambda t: t.due_date if t.due_date else "9999-99-99")

    return {
        "pending": counts["pending"],
        "in_progress": counts["in_progress"],
        "done": counts["done"],
        "cancelled": counts["cancelled"],
        "overdue": counts["overdue"],
        "todos": [t.model_dump(mode="json") for t in active_todos],
    }


# Tool definitions for the Claude API
TODOS_TOOLS = [
    {
        "name": "add_todo",
        "description": (
            "Add a new household task or chore to the family todo list. "
            "Set priority based on urgency cues."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short title of the task"},
                "description": {"type": "string", "description": "Longer description or details"},
                "assignee": {"type": "string", "description": "Family member responsible for the task"},
                "created_by": {"type": "string", "description": "Family member who created the task"},
                "due_date": {"type": "string", "description": "Due date in YYYY-MM-DD format"},
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Task priority",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization",
                },
            },
            "required": ["title"],
        },
    },
    {
        "name": "get_todos",
        "description": (
            "Return the family todo list, optionally filtered by assignee, status, "
            "or priority. Without filters, returns all non-cancelled todos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "assignee": {"type": "string", "description": "Filter to a specific family member"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "done", "cancelled"],
                    "description": "Filter by task status",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Filter by priority level",
                },
            },
            "required": [],
        },
    },
    {
        "name": "complete_todo",
        "description": "Mark a todo as done and record who completed it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "The hex ID of the todo to complete"},
                "completed_by": {"type": "string", "description": "Family member who completed the task"},
            },
            "required": ["todo_id"],
        },
    },
    {
        "name": "assign_todo",
        "description": "Assign a todo to a specific family member.",
        "input_schema": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "string", "description": "The hex ID of the todo to assign"},
                "assignee": {"type": "string", "description": "Name of the family member to assign the task to"},
            },
            "required": ["todo_id", "assignee"],
        },
    },
    {
        "name": "get_weekly_summary",
        "description": (
            "Return a summary of todos for the current week, including counts by status "
            "and a list of active (pending/in_progress) todos sorted by due date."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]

# Map tool name → function for the ReAct executor
TOOL_REGISTRY = {
    "add_todo": add_todo,
    "get_todos": get_todos,
    "complete_todo": complete_todo,
    "assign_todo": assign_todo,
    "get_weekly_summary": get_weekly_summary,
}
