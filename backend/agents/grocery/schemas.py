from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class ItemStatus(str, Enum):
    pending = "pending"
    purchased = "purchased"
    removed = "removed"


class GroceryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str = "other"
    quantity: str = "1"
    added_by: str = "unknown"
    added_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status: ItemStatus = ItemStatus.pending


class PurchaseRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str = "other"
    quantity: str = "1"
    purchased_by: str = "unknown"
    purchased_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class GroceryList(BaseModel):
    version: str = "1.0"
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    items: list[GroceryItem] = []
    purchase_history: list[PurchaseRecord] = []
