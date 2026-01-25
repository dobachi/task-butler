"""Obsidian Tasks format support.

This module provides conversion between Task Butler's internal model
and Obsidian Tasks plugin format.

Obsidian Tasks format:
- [ ] Task title 🔺 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-15 #tag1 #tag2
- [x] Completed task ✅ 2025-01-20

Emoji mapping:
- 📅 Due date
- ⏳ Scheduled date
- 🛫 Start date
- ➕ Created date
- ✅ Completion date
- 🔁 Recurrence

Priority emoji:
- 🔺 Urgent (Highest)
- ⏫ High
- 🔼 Medium
- 🔽 Low
- ⏬ Lowest
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..models.enums import Frequency, Priority, Status
from ..models.task import RecurrenceRule, Task


class ConflictResolution(str, Enum):
    """Strategy for resolving conflicts between frontmatter and Obsidian Tasks line."""

    FRONTMATTER_WINS = "frontmatter"  # Frontmatter data takes precedence
    OBSIDIAN_WINS = "obsidian"  # Obsidian Tasks line takes precedence
    NEWER_WINS = "newer"  # Use the newer modification
    ASK_USER = "ask"  # Prompt user to choose


@dataclass
class Conflict:
    """Represents a conflict between frontmatter and Obsidian Tasks line."""

    field: str
    frontmatter_value: str | None
    obsidian_value: str | None

    def __str__(self) -> str:
        return f"{self.field}: frontmatter={self.frontmatter_value}, obsidian_line={self.obsidian_value}"


@dataclass
class ParsedObsidianTask:
    """Parsed data from an Obsidian Tasks line."""

    title: str
    is_completed: bool
    priority: Priority | None
    due_date: datetime | None
    scheduled_date: datetime | None
    start_date: datetime | None
    created_at: datetime | None
    completed_at: datetime | None
    recurrence_text: str | None
    tags: list[str]


class ObsidianTasksFormat:
    """Convert between Task Butler tasks and Obsidian Tasks format."""

    # Date field emoji mapping
    EMOJI_MAP: dict[str, str] = {
        "due_date": "📅",
        "scheduled_date": "⏳",
        "start_date": "🛫",
        "created_at": "➕",
        "completed_at": "✅",
        "recurrence": "🔁",
    }

    # Reverse mapping for parsing
    EMOJI_TO_FIELD: dict[str, str] = {v: k for k, v in EMOJI_MAP.items()}

    # Priority emoji mapping (Task Butler -> Obsidian)
    PRIORITY_EMOJI: dict[Priority, str] = {
        Priority.URGENT: "🔺",
        Priority.HIGH: "⏫",
        Priority.MEDIUM: "🔼",
        Priority.LOW: "🔽",
        Priority.LOWEST: "⏬",
    }

    # Reverse mapping (Obsidian -> Task Butler)
    EMOJI_TO_PRIORITY: dict[str, Priority] = {v: k for k, v in PRIORITY_EMOJI.items()}

    # Regex patterns for parsing
    DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")
    TAG_PATTERN = re.compile(r"#(\w+)")
    CHECKBOX_PATTERN = re.compile(r"^- \[([ xX])\] ")
    RECURRENCE_PATTERN = re.compile(
        r"🔁\s*([^\s🔺⏫🔼🔽⏬📅⏳🛫➕✅#]+(?:\s+[^\s🔺⏫🔼🔽⏬📅⏳🛫➕✅#]+)*)"
    )

    def to_obsidian_line(self, task: Task) -> str:
        """Convert a Task to an Obsidian Tasks format line.

        Args:
            task: The Task to convert.

        Returns:
            A string in Obsidian Tasks format.

        Example:
            - [ ] Buy groceries 🔼 📅 2025-02-01 ⏳ 2025-01-25 #shopping
        """
        parts = []

        # Checkbox
        checkbox = "[x]" if task.status == Status.DONE else "[ ]"
        parts.append(f"- {checkbox}")

        # Title
        parts.append(task.title)

        # Priority (skip MEDIUM as it's the default)
        if task.priority != Priority.MEDIUM:
            emoji = self.PRIORITY_EMOJI.get(task.priority)
            if emoji:
                parts.append(emoji)

        # Due date
        if task.due_date:
            parts.append(f"📅 {task.due_date.strftime('%Y-%m-%d')}")

        # Scheduled date
        if task.scheduled_date:
            parts.append(f"⏳ {task.scheduled_date.strftime('%Y-%m-%d')}")

        # Start date
        if task.start_date:
            parts.append(f"🛫 {task.start_date.strftime('%Y-%m-%d')}")

        # Created date
        if task.created_at:
            parts.append(f"➕ {task.created_at.strftime('%Y-%m-%d')}")

        # Completed date
        if task.completed_at:
            parts.append(f"✅ {task.completed_at.strftime('%Y-%m-%d')}")

        # Recurrence
        if task.recurrence:
            recurrence_text = self._recurrence_to_text(task.recurrence)
            parts.append(f"🔁 {recurrence_text}")

        # Tags
        for tag in task.tags:
            parts.append(f"#{tag}")

        return " ".join(parts)

    def from_obsidian_line(self, line: str) -> ParsedObsidianTask:
        """Parse an Obsidian Tasks format line.

        Args:
            line: The line to parse.

        Returns:
            A ParsedObsidianTask with extracted data.

        Raises:
            ValueError: If the line is not a valid Obsidian Tasks line.
        """
        # Check for checkbox
        checkbox_match = self.CHECKBOX_PATTERN.match(line)
        if not checkbox_match:
            raise ValueError(f"Not a valid Obsidian Tasks line: {line}")

        is_completed = checkbox_match.group(1).lower() == "x"
        content = line[checkbox_match.end() :]

        # Extract tags
        tags = self.TAG_PATTERN.findall(content)
        # Remove tags from content for further parsing
        content_without_tags = self.TAG_PATTERN.sub("", content)

        # Extract dates with emoji
        due_date = self._extract_date(content_without_tags, "📅")
        scheduled_date = self._extract_date(content_without_tags, "⏳")
        start_date = self._extract_date(content_without_tags, "🛫")
        created_at = self._extract_date(content_without_tags, "➕")
        completed_at = self._extract_date(content_without_tags, "✅")

        # Extract recurrence
        recurrence_match = self.RECURRENCE_PATTERN.search(content_without_tags)
        recurrence_text = recurrence_match.group(1).strip() if recurrence_match else None

        # Extract priority
        priority = None
        for emoji, pri in self.EMOJI_TO_PRIORITY.items():
            if emoji in content_without_tags:
                priority = pri
                break

        # Extract title (everything before first emoji or date)
        title = self._extract_title(content_without_tags)

        return ParsedObsidianTask(
            title=title,
            is_completed=is_completed,
            priority=priority,
            due_date=due_date,
            scheduled_date=scheduled_date,
            start_date=start_date,
            created_at=created_at,
            completed_at=completed_at,
            recurrence_text=recurrence_text,
            tags=tags,
        )

    def detect_conflicts(self, task: Task, line: str) -> list[Conflict]:
        """Detect conflicts between Task data and Obsidian Tasks line.

        Args:
            task: The Task from frontmatter.
            line: The Obsidian Tasks line from the document body.

        Returns:
            A list of Conflict objects for each field that differs.
        """
        conflicts = []

        try:
            parsed = self.from_obsidian_line(line)
        except ValueError:
            return conflicts

        # Status conflict
        task_completed = task.status == Status.DONE
        if task_completed != parsed.is_completed:
            conflicts.append(
                Conflict(
                    "status",
                    task.status.value,
                    "done" if parsed.is_completed else "pending",
                )
            )

        # Priority conflict
        if parsed.priority and task.priority != parsed.priority:
            conflicts.append(
                Conflict(
                    "priority",
                    task.priority.value,
                    parsed.priority.value if parsed.priority else None,
                )
            )

        # Due date conflict
        if self._dates_differ(task.due_date, parsed.due_date):
            conflicts.append(
                Conflict(
                    "due_date",
                    task.due_date.strftime("%Y-%m-%d") if task.due_date else None,
                    parsed.due_date.strftime("%Y-%m-%d") if parsed.due_date else None,
                )
            )

        # Scheduled date conflict
        if self._dates_differ(task.scheduled_date, parsed.scheduled_date):
            conflicts.append(
                Conflict(
                    "scheduled_date",
                    task.scheduled_date.strftime("%Y-%m-%d") if task.scheduled_date else None,
                    parsed.scheduled_date.strftime("%Y-%m-%d") if parsed.scheduled_date else None,
                )
            )

        # Start date conflict
        if self._dates_differ(task.start_date, parsed.start_date):
            conflicts.append(
                Conflict(
                    "start_date",
                    task.start_date.strftime("%Y-%m-%d") if task.start_date else None,
                    parsed.start_date.strftime("%Y-%m-%d") if parsed.start_date else None,
                )
            )

        # Completed at conflict
        if self._dates_differ(task.completed_at, parsed.completed_at):
            conflicts.append(
                Conflict(
                    "completed_at",
                    task.completed_at.strftime("%Y-%m-%d") if task.completed_at else None,
                    parsed.completed_at.strftime("%Y-%m-%d") if parsed.completed_at else None,
                )
            )

        # Tags conflict
        task_tags = set(task.tags)
        parsed_tags = set(parsed.tags)
        if task_tags != parsed_tags:
            conflicts.append(
                Conflict(
                    "tags",
                    ",".join(sorted(task.tags)),
                    ",".join(sorted(parsed.tags)),
                )
            )

        return conflicts

    def parse_recurrence(self, text: str) -> RecurrenceRule | None:
        """Parse recurrence text to RecurrenceRule.

        Supports formats:
        - "daily", "weekly", "monthly", "yearly"
        - "every day", "every week", "every month", "every year"
        - "every 2 days", "every 3 weeks", etc.
        - "every week on Monday", etc.

        Args:
            text: The recurrence text to parse.

        Returns:
            A RecurrenceRule or None if parsing fails.
        """
        text = text.lower().strip()

        # Simple frequencies
        simple_map = {
            "daily": Frequency.DAILY,
            "weekly": Frequency.WEEKLY,
            "monthly": Frequency.MONTHLY,
            "yearly": Frequency.YEARLY,
            "every day": Frequency.DAILY,
            "every week": Frequency.WEEKLY,
            "every month": Frequency.MONTHLY,
            "every year": Frequency.YEARLY,
        }

        if text in simple_map:
            return RecurrenceRule(frequency=simple_map[text])

        # "every N days/weeks/months/years"
        match = re.match(r"every\s+(\d+)\s+(day|week|month|year)s?", text)
        if match:
            interval = int(match.group(1))
            unit = match.group(2)
            freq_map = {
                "day": Frequency.DAILY,
                "week": Frequency.WEEKLY,
                "month": Frequency.MONTHLY,
                "year": Frequency.YEARLY,
            }
            return RecurrenceRule(frequency=freq_map[unit], interval=interval)

        return None

    def _recurrence_to_text(self, rule: RecurrenceRule) -> str:
        """Convert RecurrenceRule to Obsidian Tasks recurrence text."""
        freq_text = {
            Frequency.DAILY: "day",
            Frequency.WEEKLY: "week",
            Frequency.MONTHLY: "month",
            Frequency.YEARLY: "year",
        }

        base = freq_text.get(rule.frequency, "day")

        if rule.interval == 1:
            return f"every {base}"
        else:
            plural = "s" if rule.interval > 1 else ""
            return f"every {rule.interval} {base}{plural}"

    def _extract_date(self, content: str, emoji: str) -> datetime | None:
        """Extract a date following a specific emoji."""
        pattern = re.compile(rf"{re.escape(emoji)}\s*(\d{{4}}-\d{{2}}-\d{{2}})")
        match = pattern.search(content)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                return None
        return None

    def _extract_title(self, content: str) -> str:
        """Extract the task title from content.

        The title is everything before the first emoji or special character.
        """
        # Remove all emoji and their associated values
        result = content

        # Remove date fields with emoji
        for emoji in ["📅", "⏳", "🛫", "➕", "✅"]:
            result = re.sub(rf"{re.escape(emoji)}\s*\d{{4}}-\d{{2}}-\d{{2}}", "", result)

        # Remove recurrence
        result = self.RECURRENCE_PATTERN.sub("", result)

        # Remove priority emoji
        for emoji in self.EMOJI_TO_PRIORITY:
            result = result.replace(emoji, "")

        # Clean up and return
        return result.strip()

    def _dates_differ(self, dt1: datetime | None, dt2: datetime | None) -> bool:
        """Check if two dates differ (comparing only the date part)."""
        if dt1 is None and dt2 is None:
            return False
        if dt1 is None or dt2 is None:
            return True
        return dt1.date() != dt2.date()
