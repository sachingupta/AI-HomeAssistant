from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class TodoStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Todo(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    description: str = ""
    assignee: str = ""
    created_by: str = "unknown"
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    due_date: Optional[str] = None
    priority: Priority = Priority.medium
    status: TodoStatus = TodoStatus.pending
    completed_by: Optional[str] = None
    completed_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class TodoStore(BaseModel):
    todos: List[Todo] = Field(default_factory=list)
    version: str = "1.0"
    updated_at: str = ""
