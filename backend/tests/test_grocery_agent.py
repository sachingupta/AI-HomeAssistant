"""
Unit tests for Grocery Agent tools.
These tests mock the Drive client so no real Google credentials are needed.
Run: pytest backend/tests/test_grocery_agent.py -v
"""

import json
from unittest.mock import MagicMock, patch

import pytest

# Patch drive functions before importing tools
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
        patch("backend.agents.grocery.tools.drive_read_json", side_effect=_mock_read),
        patch("backend.agents.grocery.tools.drive_write_json", side_effect=_mock_write),
    ):
        yield


from backend.agents.grocery.tools import (
    add_grocery_items,
    check_duplicate,
    get_grocery_list,
    get_purchase_history,
    mark_purchased,
    remove_items,
)


class TestCheckDuplicate:
    def test_no_duplicate_on_empty_list(self):
        result = check_duplicate("milk")
        assert result["is_duplicate"] is False

    def test_exact_match_is_duplicate(self):
        add_grocery_items(["organic whole milk"])
        result = check_duplicate("organic whole milk")
        assert result["is_duplicate"] is True

    def test_fuzzy_match_is_duplicate(self):
        add_grocery_items(["oat milk"])
        result = check_duplicate("oat milks")
        assert result["is_duplicate"] is True

    def test_different_item_not_duplicate(self):
        add_grocery_items(["oat milk"])
        result = check_duplicate("almond butter")
        assert result["is_duplicate"] is False


class TestAddGroceryItems:
    def test_add_single_item(self):
        result = add_grocery_items(["bananas"])
        assert "bananas" in result["added"]
        assert result["skipped_duplicates"] == []

    def test_add_multiple_items(self):
        result = add_grocery_items(["eggs", "sourdough bread", "olive oil"])
        assert len(result["added"]) == 3

    def test_duplicate_skipped(self):
        add_grocery_items(["eggs"])
        result = add_grocery_items(["eggs"])
        assert result["added"] == []
        assert len(result["skipped_duplicates"]) == 1

    def test_category_inferred_dairy(self):
        add_grocery_items(["whole milk"])
        items = get_grocery_list()["items"]
        milk = next(i for i in items if "milk" in i["name"])
        assert milk["category"] == "dairy"

    def test_category_inferred_produce(self):
        add_grocery_items(["spinach"])
        items = get_grocery_list()["items"]
        assert items[0]["category"] == "produce"


class TestGetGroceryList:
    def test_empty_list(self):
        result = get_grocery_list()
        assert result["total_items"] == 0
        assert result["items"] == []

    def test_returns_only_pending(self):
        add_grocery_items(["apples", "milk"])
        mark_purchased(["apples"])
        result = get_grocery_list()
        assert result["total_items"] == 1
        assert result["items"][0]["name"] == "milk"

    def test_categorized_groups_by_category(self):
        add_grocery_items(["milk", "cheese", "apples"])
        result = get_grocery_list(categorized=True)
        assert "dairy" in result["by_category"]
        assert "produce" in result["by_category"]


class TestMarkPurchased:
    def test_mark_existing_item(self):
        add_grocery_items(["butter"])
        result = mark_purchased(["butter"])
        assert "butter" in result["marked"]
        assert get_grocery_list()["total_items"] == 0

    def test_fuzzy_match_on_purchase(self):
        add_grocery_items(["orange juice"])
        result = mark_purchased(["OJ"])
        # OJ is too different — should be not_found (score < 70)
        assert "OJ" in result["not_found"]

    def test_not_found_item(self):
        result = mark_purchased(["unicorn tears"])
        assert "unicorn tears" in result["not_found"]

    def test_marks_go_to_history(self):
        add_grocery_items(["eggs"])
        mark_purchased(["eggs"])
        history = get_purchase_history(days=1)
        assert history["total"] == 1
        assert history["items"][0]["name"] == "eggs"


class TestRemoveItems:
    def test_remove_existing_item(self):
        add_grocery_items(["crackers"])
        result = remove_items(["crackers"])
        assert "crackers" in result["removed"]
        assert get_grocery_list()["total_items"] == 0

    def test_remove_nonexistent_item(self):
        result = remove_items(["phantom item"])
        assert "phantom item" in result["not_found"]

    def test_removed_items_not_in_history(self):
        add_grocery_items(["chips"])
        remove_items(["chips"])
        history = get_purchase_history(days=1)
        assert history["total"] == 0
