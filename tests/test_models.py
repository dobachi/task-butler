"""Tests for data models."""

from datetime import datetime

import pytest

from task_butler.models.task import Task, Note, RecurrenceRule
from task_butler.models.enums import Status, Priority, Frequency


class TestNote:
    """Tests for Note model."""

    def test_create_note(self):
        """Test creating a note."""
        note = Note(content="Test note")
        assert note.content == "Test note"
        assert isinstance(note.created_at, datetime)

    def test_note_with_timestamp(self):
        """Test creating a note with specific timestamp."""
        ts = datetime(2024, 1, 15, 10, 30)
        note = Note(content="Test", created_at=ts)
        assert note.created_at == ts


class TestRecurrenceRule:
    """Tests for RecurrenceRule model."""

    def test_daily_recurrence(self):
        """Test daily recurrence rule."""
        rule = RecurrenceRule(frequency=Frequency.DAILY)
        assert rule.frequency == Frequency.DAILY
        assert rule.interval == 1

    def test_weekly_recurrence_with_days(self):
        """Test weekly recurrence with specific days."""
        rule = RecurrenceRule(
            frequency=Frequency.WEEKLY,
            days_of_week=[0, 2, 4],  # Mon, Wed, Fri
        )
        assert rule.frequency == Frequency.WEEKLY
        assert rule.days_of_week == [0, 2, 4]

    def test_monthly_recurrence_with_day(self):
        """Test monthly recurrence with specific day."""
        rule = RecurrenceRule(
            frequency=Frequency.MONTHLY,
            day_of_month=15,
        )
        assert rule.day_of_month == 15

    def test_recurrence_with_interval(self):
        """Test recurrence with interval."""
        rule = RecurrenceRule(
            frequency=Frequency.WEEKLY,
            interval=2,  # Every 2 weeks
        )
        assert rule.interval == 2

    def test_recurrence_with_end_date(self):
        """Test recurrence with end date."""
        end = datetime(2024, 12, 31)
        rule = RecurrenceRule(
            frequency=Frequency.DAILY,
            end_date=end,
        )
        assert rule.end_date == end


class TestTask:
    """Tests for Task model."""

    def test_create_minimal_task(self):
        """Test creating a task with minimal fields."""
        task = Task(title="Test task")
        assert task.title == "Test task"
        assert task.status == Status.PENDING
        assert task.priority == Priority.MEDIUM
        assert task.description == ""
        assert task.tags == []
        assert len(task.id) == 36  # UUID format

    def test_create_full_task(self):
        """Test creating a task with all fields."""
        due = datetime(2024, 2, 1)
        task = Task(
            title="Full task",
            description="Description here",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
            due_date=due,
            estimated_hours=4.5,
            tags=["work", "important"],
            project="project-a",
        )
        assert task.title == "Full task"
        assert task.description == "Description here"
        assert task.status == Status.IN_PROGRESS
        assert task.priority == Priority.HIGH
        assert task.due_date == due
        assert task.estimated_hours == 4.5
        assert task.tags == ["work", "important"]
        assert task.project == "project-a"

    def test_task_with_parent(self):
        """Test task with parent."""
        parent = Task(title="Parent")
        child = Task(title="Child", parent_id=parent.id)
        assert child.parent_id == parent.id

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        dep1 = Task(title="Dependency 1")
        dep2 = Task(title="Dependency 2")
        task = Task(title="Main", dependencies=[dep1.id, dep2.id])
        assert len(task.dependencies) == 2
        assert dep1.id in task.dependencies

    def test_add_note(self):
        """Test adding a note to a task."""
        task = Task(title="Test")
        original_updated = task.updated_at

        task.add_note("First note")
        assert len(task.notes) == 1
        assert task.notes[0].content == "First note"
        assert task.updated_at >= original_updated

    def test_start_task(self):
        """Test starting a task."""
        task = Task(title="Test")
        assert task.status == Status.PENDING

        task.start()
        assert task.status == Status.IN_PROGRESS

    def test_complete_task(self):
        """Test completing a task."""
        task = Task(title="Test", estimated_hours=2.0)
        task.start()
        task.complete(actual_hours=1.5)

        assert task.status == Status.DONE
        assert task.actual_hours == 1.5
        assert task.completed_at is not None
        assert isinstance(task.completed_at, datetime)

    def test_cancel_task(self):
        """Test cancelling a task."""
        task = Task(title="Test")
        task.cancel()
        assert task.status == Status.CANCELLED

    def test_is_open(self):
        """Test is_open property."""
        task = Task(title="Test")
        assert task.is_open is True

        task.start()
        assert task.is_open is True

        task.complete()
        assert task.is_open is False

    def test_is_recurring(self):
        """Test is_recurring property."""
        task = Task(title="Test")
        assert task.is_recurring is False

        recurring_task = Task(
            title="Recurring",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )
        assert recurring_task.is_recurring is True

    def test_is_recurrence_instance(self):
        """Test is_recurrence_instance property."""
        parent = Task(
            title="Parent",
            recurrence=RecurrenceRule(frequency=Frequency.DAILY),
        )
        instance = Task(
            title="Instance",
            recurrence_parent_id=parent.id,
        )

        assert parent.is_recurrence_instance is False
        assert instance.is_recurrence_instance is True

    def test_short_id(self):
        """Test short_id property."""
        task = Task(title="Test")
        assert len(task.short_id) == 8
        assert task.id.startswith(task.short_id)

    def test_task_with_obsidian_date_fields(self):
        """Test task with Obsidian-compatible date fields."""
        due = datetime(2025, 2, 1)
        scheduled = datetime(2025, 1, 25)
        start = datetime(2025, 1, 20)

        task = Task(
            title="Obsidian task",
            due_date=due,
            scheduled_date=scheduled,
            start_date=start,
        )

        assert task.due_date == due
        assert task.scheduled_date == scheduled
        assert task.start_date == start
        assert task.completed_at is None

    def test_priority_lowest(self):
        """Test LOWEST priority level."""
        task = Task(title="Low priority task", priority=Priority.LOWEST)
        assert task.priority == Priority.LOWEST
        assert task.priority.value == "lowest"
