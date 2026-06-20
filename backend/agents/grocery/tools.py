"""
Grocery Agent tool implementations.
Each function is also registered as a Claude tool in agent.py.
All storage access goes through data_client — swap DATA_STORE env var to switch backends.
"""

import json
from datetime import datetime, timezone, timedelta

from rapidfuzz import fuzz

from backend.data_client import store_read_json, store_write_json
from backend.agents.grocery.schemas import GroceryItem, GroceryList, ItemStatus, PurchaseRecord

_FOLDER = "groceries"
_FILE = "grocery_list.json"

_CATEGORIES = {
    "produce": ["apple", "banana", "berry", "berries", "grape", "orange", "lemon", "lime",
                "avocado", "tomato", "lettuce", "spinach", "kale", "carrot", "broccoli",
                "onion", "garlic", "pepper", "cucumber", "zucchini", "mushroom", "celery",
                "ginger", "herbs", "fruit", "vegetable", "salad"],
    "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "egg", "eggs", "sour cream",
              "cream cheese", "cottage cheese", "whipping cream", "half and half"],
    "meat": ["chicken", "beef", "pork", "steak", "ground", "turkey", "salmon", "fish",
             "shrimp", "tuna", "bacon", "sausage", "ham", "lamb", "ribs"],
    "bakery": ["bread", "sourdough", "bagel", "muffin", "croissant", "roll", "baguette",
               "tortilla", "pita", "naan"],
    "frozen": ["frozen", "ice cream", "pizza", "waffle", "ice", "popsicle"],
    "pantry": ["pasta", "rice", "flour", "sugar", "oil", "vinegar", "sauce", "soup",
               "beans", "lentils", "cereal", "oats", "granola", "crackers", "chips",
               "salsa", "peanut butter", "jelly", "jam", "honey", "syrup", "ketchup",
               "mustard", "mayo", "dressing", "spice", "salt", "pepper", "broth",
               "canned", "can", "snack", "nut", "nuts", "seeds", "coffee", "tea"],
    "beverages": ["juice", "water", "soda", "sparkling", "wine", "beer", "kombucha",
                  "lemonade", "milk alternative", "oat milk", "almond milk"],
    "household": ["paper towel", "toilet paper", "soap", "shampoo", "conditioner",
                  "detergent", "dish", "sponge", "trash", "bag", "foil", "wrap",
                  "ziplock", "cleaner", "bleach", "toothpaste", "toothbrush"],
}


def _infer_category(item_name: str) -> str:
    name_lower = item_name.lower()
    for category, keywords in _CATEGORIES.items():
        if any(kw in name_lower for kw in keywords):
            return category
    return "other"


def _load_list() -> GroceryList:
    data = store_read_json(_FOLDER, _FILE)
    if not data:
        return GroceryList()
    return GroceryList.model_validate(data)


def _save_list(grocery_list: GroceryList) -> None:
    grocery_list.updated_at = datetime.now(timezone.utc).isoformat()
    store_write_json(_FOLDER, _FILE, grocery_list.model_dump(mode="json"))


def check_duplicate(item: str) -> dict:
    """Fuzzy-match an item name against the current pending grocery list.

    Args:
        item: Item name to check for duplicates.

    Returns:
        dict with 'is_duplicate' bool, and 'matched_item' if found.
    """
    grocery_list = _load_list()
    pending = [i for i in grocery_list.items if i.status == ItemStatus.pending]
    for existing in pending:
        score = fuzz.token_set_ratio(item.lower(), existing.name.lower())
        if score >= 80:
            return {"is_duplicate": True, "matched_item": existing.name, "score": score}
    return {"is_duplicate": False, "matched_item": None}


def add_grocery_items(items: list[str], added_by: str = "unknown") -> dict:
    """Add one or more items to the grocery list, skipping duplicates.

    Args:
        items: List of item name strings to add.
        added_by: Name of the family member adding the items.

    Returns:
        dict with 'added' list and 'skipped_duplicates' list.
    """
    grocery_list = _load_list()
    added = []
    skipped = []

    for item_name in items:
        dup = check_duplicate(item_name)
        if dup["is_duplicate"]:
            skipped.append({"requested": item_name, "existing": dup["matched_item"]})
            continue
        new_item = GroceryItem(
            name=item_name.strip(),
            category=_infer_category(item_name),
            added_by=added_by,
        )
        grocery_list.items.append(new_item)
        added.append(new_item.name)

    _save_list(grocery_list)
    return {"added": added, "skipped_duplicates": skipped}


def get_grocery_list(categorized: bool = False) -> dict:
    """Return the current pending grocery list.

    Args:
        categorized: If True, group items by category.

    Returns:
        dict with items list or categorized dict.
    """
    grocery_list = _load_list()
    pending = [i for i in grocery_list.items if i.status == ItemStatus.pending]

    if not categorized:
        return {
            "total_items": len(pending),
            "items": [{"name": i.name, "quantity": i.quantity, "category": i.category}
                      for i in pending],
        }

    by_category: dict[str, list] = {}
    for item in pending:
        by_category.setdefault(item.category, []).append(
            {"name": item.name, "quantity": item.quantity}
        )
    return {"total_items": len(pending), "by_category": by_category}


def mark_purchased(items: list[str], purchased_by: str = "unknown") -> dict:
    """Mark items as purchased and move them to purchase history.

    Args:
        items: List of item names to mark as purchased.
        purchased_by: Name of the family member who bought the items.

    Returns:
        dict with 'marked' and 'not_found' lists.
    """
    grocery_list = _load_list()
    marked = []
    not_found = []

    for item_name in items:
        matched = None
        best_score = 0
        for i in grocery_list.items:
            if i.status != ItemStatus.pending:
                continue
            score = fuzz.token_set_ratio(item_name.lower(), i.name.lower())
            if score > best_score:
                best_score = score
                matched = i

        if matched and best_score >= 70:
            matched.status = ItemStatus.purchased
            grocery_list.purchase_history.append(
                PurchaseRecord(
                    name=matched.name,
                    category=matched.category,
                    quantity=matched.quantity,
                    purchased_by=purchased_by,
                )
            )
            marked.append(matched.name)
        else:
            not_found.append(item_name)

    _save_list(grocery_list)
    return {"marked": marked, "not_found": not_found}


def remove_items(items: list[str]) -> dict:
    """Remove items from the list without marking them as purchased.

    Args:
        items: List of item names to remove.

    Returns:
        dict with 'removed' and 'not_found' lists.
    """
    grocery_list = _load_list()
    removed = []
    not_found = []

    for item_name in items:
        matched = None
        best_score = 0
        for i in grocery_list.items:
            if i.status != ItemStatus.pending:
                continue
            score = fuzz.token_set_ratio(item_name.lower(), i.name.lower())
            if score > best_score:
                best_score = score
                matched = i

        if matched and best_score >= 70:
            matched.status = ItemStatus.removed
            removed.append(matched.name)
        else:
            not_found.append(item_name)

    _save_list(grocery_list)
    return {"removed": removed, "not_found": not_found}


def get_purchase_history(days: int = 7) -> dict:
    """Return items purchased in the last N days.

    Args:
        days: Number of days to look back.

    Returns:
        dict with 'items' list and 'total' count.
    """
    grocery_list = _load_list()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for record in grocery_list.purchase_history:
        purchased_at = datetime.fromisoformat(record.purchased_at.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        if purchased_at >= cutoff:
            recent.append({
                "name": record.name,
                "category": record.category,
                "purchased_by": record.purchased_by,
                "purchased_at": record.purchased_at,
            })
    return {"days": days, "total": len(recent), "items": recent}


# Tool definitions for the Claude API
GROCERY_TOOLS = [
    {
        "name": "check_duplicate",
        "description": "Fuzzy-match an item name against the current grocery list to detect duplicates before adding.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Item name to check"}
            },
            "required": ["item"],
        },
    },
    {
        "name": "add_grocery_items",
        "description": "Add one or more items to the family grocery list. Always check for duplicates first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of item names to add",
                },
                "added_by": {
                    "type": "string",
                    "description": "Name of the family member adding items",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "get_grocery_list",
        "description": "Return the current pending grocery list, optionally grouped by category/aisle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "categorized": {
                    "type": "boolean",
                    "description": "If true, group items by category for efficient shopping",
                }
            },
            "required": [],
        },
    },
    {
        "name": "mark_purchased",
        "description": "Mark one or more items as purchased and move them to purchase history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Item names to mark as purchased",
                },
                "purchased_by": {
                    "type": "string",
                    "description": "Family member who purchased the items",
                },
            },
            "required": ["items"],
        },
    },
    {
        "name": "remove_items",
        "description": "Remove items from the grocery list without marking them as purchased.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Item names to remove",
                }
            },
            "required": ["items"],
        },
    },
    {
        "name": "get_purchase_history",
        "description": "Return items purchased in the last N days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 7)",
                }
            },
            "required": [],
        },
    },
]

# Map tool name → function for the ReAct executor
TOOL_REGISTRY = {
    "check_duplicate": check_duplicate,
    "add_grocery_items": add_grocery_items,
    "get_grocery_list": get_grocery_list,
    "mark_purchased": mark_purchased,
    "remove_items": remove_items,
    "get_purchase_history": get_purchase_history,
}
