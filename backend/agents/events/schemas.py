from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class RecurringRule(BaseModel):
    frequency: str
    until: str  # ISO date string


class Event(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str
    datetime_str: str = Field(alias="datetime")
    duration_minutes: int = 60
    location: str = ""
    participants: list = Field(default_factory=list)
    driver: str = ""
    recurring: Optional[RecurringRule] = None
    notes: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class EventStore(BaseModel):
    events: list = Field(default_factory=list)
    version: str = "1.0"
    updated_at: str = ""
