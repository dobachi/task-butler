"""Task data models."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import Frequency, Priority, Status


class Note(BaseModel):
    """A note attached to a task."""

    content: str
    created_at: datetime = Field(default_factory=datetime.now)


class RecurrenceRule(BaseModel):
    """Rule for recurring tasks."""

    frequency: Frequency
    interval: int = 1  # Every N periods (2 = every other week, etc.)
    days_of_week: list[int] | None = None  # 0=Monday to 6=Sunday
    day_of_month: int | None = None
    end_date: datetime | None = None


class Task(BaseModel):
    """A task with full metadata."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str = ""
    status: Status = Status.PENDING
    priority: Priority = Priority.MEDIUM

    # Time-related
    due_date: datetime | None = None  # 📅 Due date
    scheduled_date: datetime | None = None  # ⏳ Scheduled date (when to work on it)
    start_date: datetime | None = None  # 🛫 Start date (when work begins)
    completed_at: datetime | None = None  # ✅ Completion timestamp
    estimated_hours: float | None = None
    actual_hours: float | None = None

    # Classification
    tags: list[str] = Field(default_factory=list)
    project: str | None = None

    # Hierarchy and dependencies
    parent_id: str | None = None  # Parent task for hierarchical structure
    dependencies: list[str] = Field(default_factory=list)  # IDs of tasks this depends on

    # Recurrence
    recurrence: RecurrenceRule | None = None
    recurrence_parent_id: str | None = None  # Original task for recurrence instances

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    notes: list[Note] = Field(default_factory=list)

    # Source tracking (for imports)
    source_file: str | None = None  # Original file path (relative to Vault)
    source_line: int | None = None  # Original line number in source file

    def add_note(self, content: str) -> None:
        """Add a note to the task."""
        self.notes.append(Note(content=content))
        self.updated_at = datetime.now()

    def start(self) -> None:
        """Mark task as in progress."""
        self.status = Status.IN_PROGRESS
        self.updated_at = datetime.now()

    def complete(self, actual_hours: float | None = None) -> None:
        """Mark task as done."""
        self.status = Status.DONE
        self.completed_at = datetime.now()
        if actual_hours is not None:
            self.actual_hours = actual_hours
        self.updated_at = datetime.now()

    def cancel(self) -> None:
        """Mark task as cancelled."""
        self.status = Status.CANCELLED
        self.updated_at = datetime.now()

    @property
    def is_open(self) -> bool:
        """Check if task is still open (pending or in progress)."""
        return self.status in (Status.PENDING, Status.IN_PROGRESS)

    @property
    def is_recurring(self) -> bool:
        """Check if this is a recurring task template."""
        return self.recurrence is not None

    @property
    def is_recurrence_instance(self) -> bool:
        """Check if this is an instance of a recurring task."""
        return self.recurrence_parent_id is not None

    @property
    def short_id(self) -> str:
        """Return first 8 characters of ID for display."""
        return self.id[:8]
