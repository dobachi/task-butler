"""Enumerations for Task Butler."""

from enum import Enum


class Status(str, Enum):
    """Task status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Task priority levels.

    Maps to Obsidian Tasks emoji:
    - LOWEST: ⏬
    - LOW: 🔽
    - MEDIUM: 🔼
    - HIGH: ⏫
    - URGENT: 🔺
    """

    LOWEST = "lowest"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Frequency(str, Enum):
    """Recurrence frequency."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
