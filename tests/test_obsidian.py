"""Tests for Obsidian Tasks format support."""

from datetime import datetime

import pytest

from task_butler.models.task import Task, RecurrenceRule
from task_butler.models.enums import Status, Priority, Frequency
from task_butler.storage.obsidian import (
    ObsidianTasksFormat,
    ParsedObsidianTask,
    Conflict,
    ConflictResolution,
)


class TestObsidianTasksFormat:
    """Tests for ObsidianTasksFormat class."""

    @pytest.fixture
    def formatter(self):
        """Create an ObsidianTasksFormat instance."""
        return ObsidianTasksFormat()

    def test_to_obsidian_line_minimal(self, formatter):
        """Test converting a minimal task to Obsidian format."""
        task = Task(title="Buy groceries")
        line = formatter.to_obsidian_line(task)

        assert line.startswith("- [ ]")
        assert "Buy groceries" in line
        # MEDIUM priority is default, no emoji
        assert "🔼" not in line

    def test_to_obsidian_line_completed(self, formatter):
        """Test converting a completed task."""
        task = Task(title="Done task")
        task.complete()
        line = formatter.to_obsidian_line(task)

        assert line.startswith("- [x]")
        assert "Done task" in line
        assert "✅" in line

    def test_to_obsidian_line_with_priority(self, formatter):
        """Test priority emoji mapping."""
        priorities = [
            (Priority.URGENT, "🔺"),
            (Priority.HIGH, "⏫"),
            (Priority.MEDIUM, None),  # No emoji for default
            (Priority.LOW, "🔽"),
            (Priority.LOWEST, "⏬"),
        ]

        for priority, expected_emoji in priorities:
            task = Task(title="Test", priority=priority)
            line = formatter.to_obsidian_line(task)

            if expected_emoji:
                assert expected_emoji in line
            else:
                # MEDIUM has no emoji
                for emoji in ["🔺", "⏫", "🔽", "⏬"]:
                    assert emoji not in line

    def test_to_obsidian_line_with_dates(self, formatter):
        """Test date field conversion."""
        task = Task(
            title="Task with dates",
            due_date=datetime(2025, 2, 1),
            scheduled_date=datetime(2025, 1, 25),
            start_date=datetime(2025, 1, 20),
        )
        line = formatter.to_obsidian_line(task)

        assert "📅 2025-02-01" in line
        assert "⏳ 2025-01-25" in line
        assert "🛫 2025-01-20" in line

    def test_to_obsidian_line_with_tags(self, formatter):
        """Test tag conversion."""
        task = Task(title="Tagged task", tags=["work", "important"])
        line = formatter.to_obsidian_line(task)

        assert "#work" in line
        assert "#important" in line

    def test_to_obsidian_line_with_recurrence(self, formatter):
        """Test recurrence conversion."""
        task = Task(
            title="Weekly task",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )
        line = formatter.to_obsidian_line(task)

        assert "🔁" in line
        assert "every week" in line

    def test_to_obsidian_line_with_interval_recurrence(self, formatter):
        """Test recurrence with interval."""
        task = Task(
            title="Bi-weekly task",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY, interval=2),
        )
        line = formatter.to_obsidian_line(task)

        assert "every 2 weeks" in line

    def test_from_obsidian_line_minimal(self, formatter):
        """Test parsing a minimal Obsidian Tasks line."""
        line = "- [ ] Buy groceries"
        parsed = formatter.from_obsidian_line(line)

        assert parsed.title == "Buy groceries"
        assert parsed.is_completed is False
        assert parsed.priority is None
        assert parsed.due_date is None

    def test_from_obsidian_line_completed(self, formatter):
        """Test parsing a completed task."""
        line = "- [x] Done task ✅ 2025-01-20"
        parsed = formatter.from_obsidian_line(line)

        assert parsed.is_completed is True
        assert parsed.completed_at == datetime(2025, 1, 20)

    def test_from_obsidian_line_with_priority(self, formatter):
        """Test parsing priority emoji."""
        test_cases = [
            ("- [ ] Task 🔺", Priority.URGENT),
            ("- [ ] Task ⏫", Priority.HIGH),
            ("- [ ] Task 🔼", Priority.MEDIUM),
            ("- [ ] Task 🔽", Priority.LOW),
            ("- [ ] Task ⏬", Priority.LOWEST),
        ]

        for line, expected_priority in test_cases:
            parsed = formatter.from_obsidian_line(line)
            assert parsed.priority == expected_priority

    def test_from_obsidian_line_with_dates(self, formatter):
        """Test parsing date fields."""
        line = "- [ ] Task 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20"
        parsed = formatter.from_obsidian_line(line)

        assert parsed.due_date == datetime(2025, 2, 1)
        assert parsed.scheduled_date == datetime(2025, 1, 25)
        assert parsed.start_date == datetime(2025, 1, 20)

    def test_from_obsidian_line_with_tags(self, formatter):
        """Test parsing tags."""
        line = "- [ ] Task #work #important #urgent"
        parsed = formatter.from_obsidian_line(line)

        assert "work" in parsed.tags
        assert "important" in parsed.tags
        assert "urgent" in parsed.tags

    def test_from_obsidian_line_with_recurrence(self, formatter):
        """Test parsing recurrence."""
        line = "- [ ] Task 🔁 every week"
        parsed = formatter.from_obsidian_line(line)

        assert parsed.recurrence_text == "every week"

    def test_from_obsidian_line_full(self, formatter):
        """Test parsing a fully-featured Obsidian Tasks line."""
        line = "- [ ] Important meeting 🔺 📅 2025-02-01 ⏳ 2025-01-25 🛫 2025-01-20 ➕ 2025-01-15 🔁 every week #work #important"
        parsed = formatter.from_obsidian_line(line)

        assert "Important meeting" in parsed.title
        assert parsed.is_completed is False
        assert parsed.priority == Priority.URGENT
        assert parsed.due_date == datetime(2025, 2, 1)
        assert parsed.scheduled_date == datetime(2025, 1, 25)
        assert parsed.start_date == datetime(2025, 1, 20)
        assert parsed.created_at == datetime(2025, 1, 15)
        assert parsed.recurrence_text == "every week"
        assert "work" in parsed.tags
        assert "important" in parsed.tags

    def test_from_obsidian_line_invalid(self, formatter):
        """Test parsing an invalid line."""
        with pytest.raises(ValueError):
            formatter.from_obsidian_line("Not a task line")

    def test_roundtrip(self, formatter):
        """Test that a task can be converted to Obsidian format and back."""
        original = Task(
            title="Roundtrip test",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
            scheduled_date=datetime(2025, 1, 25),
            tags=["test", "roundtrip"],
        )

        line = formatter.to_obsidian_line(original)
        parsed = formatter.from_obsidian_line(line)

        assert "Roundtrip test" in parsed.title
        assert parsed.priority == Priority.HIGH
        assert parsed.due_date == datetime(2025, 2, 1)
        assert parsed.scheduled_date == datetime(2025, 1, 25)
        assert "test" in parsed.tags
        assert "roundtrip" in parsed.tags


class TestConflictDetection:
    """Tests for conflict detection between frontmatter and Obsidian Tasks line."""

    @pytest.fixture
    def formatter(self):
        """Create an ObsidianTasksFormat instance."""
        return ObsidianTasksFormat()

    def test_no_conflicts(self, formatter):
        """Test when there are no conflicts."""
        task = Task(
            title="Test",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
        )
        line = "- [ ] Test ⏫ 📅 2025-02-01"

        conflicts = formatter.detect_conflicts(task, line)
        assert len(conflicts) == 0

    def test_status_conflict(self, formatter):
        """Test detecting status conflict."""
        task = Task(title="Test", status=Status.PENDING)
        line = "- [x] Test"

        conflicts = formatter.detect_conflicts(task, line)

        assert len(conflicts) == 1
        assert conflicts[0].field == "status"
        assert conflicts[0].frontmatter_value == "pending"
        assert conflicts[0].obsidian_value == "done"

    def test_priority_conflict(self, formatter):
        """Test detecting priority conflict."""
        task = Task(title="Test", priority=Priority.LOW)
        line = "- [ ] Test 🔺"  # URGENT priority

        conflicts = formatter.detect_conflicts(task, line)

        priority_conflict = next((c for c in conflicts if c.field == "priority"), None)
        assert priority_conflict is not None
        assert priority_conflict.frontmatter_value == "low"
        assert priority_conflict.obsidian_value == "urgent"

    def test_due_date_conflict(self, formatter):
        """Test detecting due date conflict."""
        task = Task(title="Test", due_date=datetime(2025, 2, 1))
        line = "- [ ] Test 📅 2025-03-01"

        conflicts = formatter.detect_conflicts(task, line)

        date_conflict = next((c for c in conflicts if c.field == "due_date"), None)
        assert date_conflict is not None
        assert date_conflict.frontmatter_value == "2025-02-01"
        assert date_conflict.obsidian_value == "2025-03-01"

    def test_tags_conflict(self, formatter):
        """Test detecting tags conflict."""
        task = Task(title="Test", tags=["work", "important"])
        line = "- [ ] Test #work #urgent"  # 'important' replaced with 'urgent'

        conflicts = formatter.detect_conflicts(task, line)

        tags_conflict = next((c for c in conflicts if c.field == "tags"), None)
        assert tags_conflict is not None

    def test_multiple_conflicts(self, formatter):
        """Test detecting multiple conflicts."""
        task = Task(
            title="Test",
            status=Status.PENDING,
            priority=Priority.LOW,
            due_date=datetime(2025, 2, 1),
        )
        line = "- [x] Test 🔺 📅 2025-03-01"  # Different status, priority, and date

        conflicts = formatter.detect_conflicts(task, line)

        assert len(conflicts) >= 3
        fields = [c.field for c in conflicts]
        assert "status" in fields
        assert "priority" in fields
        assert "due_date" in fields


class TestRecurrenceParsing:
    """Tests for recurrence text parsing."""

    @pytest.fixture
    def formatter(self):
        """Create an ObsidianTasksFormat instance."""
        return ObsidianTasksFormat()

    def test_parse_simple_frequencies(self, formatter):
        """Test parsing simple frequency words."""
        test_cases = [
            ("daily", Frequency.DAILY, 1),
            ("weekly", Frequency.WEEKLY, 1),
            ("monthly", Frequency.MONTHLY, 1),
            ("yearly", Frequency.YEARLY, 1),
            ("every day", Frequency.DAILY, 1),
            ("every week", Frequency.WEEKLY, 1),
            ("every month", Frequency.MONTHLY, 1),
            ("every year", Frequency.YEARLY, 1),
        ]

        for text, expected_freq, expected_interval in test_cases:
            rule = formatter.parse_recurrence(text)
            assert rule is not None
            assert rule.frequency == expected_freq
            assert rule.interval == expected_interval

    def test_parse_interval_recurrence(self, formatter):
        """Test parsing recurrence with intervals."""
        test_cases = [
            ("every 2 days", Frequency.DAILY, 2),
            ("every 3 weeks", Frequency.WEEKLY, 3),
            ("every 6 months", Frequency.MONTHLY, 6),
            ("every 2 years", Frequency.YEARLY, 2),
        ]

        for text, expected_freq, expected_interval in test_cases:
            rule = formatter.parse_recurrence(text)
            assert rule is not None
            assert rule.frequency == expected_freq
            assert rule.interval == expected_interval

    def test_parse_invalid_recurrence(self, formatter):
        """Test parsing invalid recurrence text."""
        result = formatter.parse_recurrence("invalid text")
        assert result is None
