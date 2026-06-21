"""
Unit tests for Todos Agent tools.
These tests mock the store client so no real Google credentials are needed.
Run: pytest backend/tests/test_todos_agent.py -v
"""

from datetime import datetime, timezone, timedelta
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
        patch("backend.agents.todos.tools.store_read_json", side_effect=_mock_read),
        patch("backend.agents.todos.tools.store_write_json", side_effect=_mock_write),
    ):
        yield


from backend.agents.todos.tools import (
    add_todo,
    get_todos,
    complete_todo,
    assign_todo,
    get_weekly_summary,
)


class TestAddTodo:
    def test_add_todo_returns_added_dict(self):
        result = add_todo("Mow the lawn")
        assert "added" in result
        assert result["added"]["title"] == "Mow the lawn"

    def test_added_todo_has_correct_defaults(self):
        result = add_todo("Take out trash")
        todo = result["added"]
        assert todo["status"] == "pending"
        assert todo["priority"] == "medium"
        assert todo["assignee"] == ""
        assert todo["created_by"] == "unknown"

    def test_add_todo_with_all_fields(self):
        result = add_todo(
            title="Fix the fence",
            description="Back yard fence is broken",
            assignee="dad",
            created_by="mom",
            due_date="2026-06-21",
            priority="high",
            tags=["outdoor", "repair"],
        )
        todo = result["added"]
        assert todo["title"] == "Fix the fence"
        assert todo["description"] == "Back yard fence is broken"
        assert todo["assignee"] == "dad"
        assert todo["created_by"] == "mom"
        assert todo["due_date"] == "2026-06-21"
        assert todo["priority"] == "high"
        assert todo["tags"] == ["outdoor", "repair"]
        assert "id" in todo


class TestGetTodos:
    def test_get_all_todos_no_filter(self):
        add_todo("Task 1")
        add_todo("Task 2")
        result = get_todos()
        assert result["total"] == 2
        assert len(result["todos"]) == 2

    def test_filter_by_assignee(self):
        add_todo("Dad's task", assignee="dad")
        add_todo("Mom's task", assignee="mom")
        result = get_todos(assignee="dad")
        assert result["total"] == 1
        assert result["todos"][0]["assignee"] == "dad"

    def test_filter_by_status(self):
        add_todo("Pending task")
        r = add_todo("Task to complete")
        complete_todo(r["added"]["id"], completed_by="dad")
        result = get_todos(status="done")
        assert result["total"] == 1
        assert result["todos"][0]["status"] == "done"

    def test_filter_by_priority(self):
        add_todo("Low priority task", priority="low")
        add_todo("High priority task", priority="high")
        result = get_todos(priority="high")
        assert result["total"] == 1
        assert result["todos"][0]["priority"] == "high"

    def test_cancelled_todos_excluded_by_default(self):
        add_todo("Normal task")
        r = add_todo("Cancelled task")
        todo_id = r["added"]["id"]

        from backend.agents.todos.schemas import TodoStore, TodoStatus
        store_data = _MOCK_STORE.get("todos/todos.json", {})
        store = TodoStore.model_validate(store_data)
        for t in store.todos:
            if t.id == todo_id:
                t.status = TodoStatus.cancelled
        _MOCK_STORE["todos/todos.json"] = store.model_dump(mode="json")

        result = get_todos()
        assert result["total"] == 1
        assert result["todos"][0]["title"] == "Normal task"

    def test_todos_sorted_by_due_date_then_priority(self):
        add_todo("Later high", due_date="2026-06-25", priority="high")
        add_todo("Earlier low", due_date="2026-06-20", priority="low")
        add_todo("Earlier high", due_date="2026-06-20", priority="high")
        result = get_todos()
        titles = [t["title"] for t in result["todos"]]
        assert titles.index("Earlier high") < titles.index("Earlier low")
        assert titles.index("Earlier high") < titles.index("Later high")


class TestCompleteTodo:
    def test_complete_existing_todo(self):
        r = add_todo("Clean the kitchen")
        result = complete_todo(r["added"]["id"])
        assert result["completed"] is True

    def test_complete_sets_completed_by_and_status(self):
        r = add_todo("Wash the car")
        todo_id = r["added"]["id"]
        complete_todo(todo_id, completed_by="son")

        from backend.agents.todos.schemas import TodoStore
        store = TodoStore.model_validate(_MOCK_STORE.get("todos/todos.json", {}))
        todo = next(t for t in store.todos if t.id == todo_id)
        assert todo.status.value == "done"
        assert todo.completed_by == "son"
        assert todo.completed_at is not None

    def test_complete_nonexistent_todo(self):
        result = complete_todo("nonexistent-id-12345")
        assert result["completed"] is False
        assert result["title"] is None


class TestAssignTodo:
    def test_assign_changes_assignee(self):
        r = add_todo("Paint the garage")
        todo_id = r["added"]["id"]
        result = assign_todo(todo_id, "dad")
        assert result["assigned"] is True

        from backend.agents.todos.schemas import TodoStore
        store = TodoStore.model_validate(_MOCK_STORE.get("todos/todos.json", {}))
        todo = next(t for t in store.todos if t.id == todo_id)
        assert todo.assignee == "dad"

    def test_assign_nonexistent_todo(self):
        result = assign_todo("does-not-exist-abc", "mom")
        assert result["assigned"] is False


class TestGetWeeklySummary:
    def test_summary_counts_by_status(self):
        r1 = add_todo("Pending task 1")
        r2 = add_todo("Pending task 2")
        r3 = add_todo("Task to complete")
        r4 = add_todo("Task to cancel")

        complete_todo(r3["added"]["id"], completed_by="mom")

        from backend.agents.todos.schemas import TodoStore, TodoStatus
        store_data = _MOCK_STORE.get("todos/todos.json", {})
        store = TodoStore.model_validate(store_data)
        for t in store.todos:
            if t.id == r4["added"]["id"]:
                t.status = TodoStatus.cancelled
        _MOCK_STORE["todos/todos.json"] = store.model_dump(mode="json")

        result = get_weekly_summary()
        assert result["pending"] == 2
        assert result["done"] == 1
        assert result["cancelled"] == 1
        assert len(result["todos"]) == 2
        assert "overdue" in result
