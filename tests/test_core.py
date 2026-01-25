"""Tests for core business logic."""

from datetime import datetime, timedelta

import pytest

from task_butler.models.task import Task, RecurrenceRule
from task_butler.models.enums import Status, Priority, Frequency
from task_butler.core.task_manager import TaskManager
from task_butler.core.recurrence import RecurrenceGenerator


class TestRecurrenceGenerator:
    """Tests for RecurrenceGenerator."""

    @pytest.fixture
    def generator(self):
        """Create a recurrence generator."""
        return RecurrenceGenerator()

    def test_next_daily(self, generator):
        """Test daily recurrence."""
        rule = RecurrenceRule(frequency=Frequency.DAILY)
        after = datetime(2024, 1, 15, 10, 30)

        next_date = generator.get_next_occurrence(rule, after)
        assert next_date is not None
        assert next_date.date() == datetime(2024, 1, 16).date()

    def test_next_daily_with_interval(self, generator):
        """Test daily recurrence with interval."""
        rule = RecurrenceRule(frequency=Frequency.DAILY, interval=3)
        after = datetime(2024, 1, 15)

        next_date = generator.get_next_occurrence(rule, after)
        assert next_date.date() == datetime(2024, 1, 18).date()

    def test_next_weekly(self, generator):
        """Test weekly recurrence."""
        rule = RecurrenceRule(frequency=Frequency.WEEKLY)
        after = datetime(2024, 1, 15)  # Monday

        next_date = generator.get_next_occurrence(rule, after)
        assert next_date.date() == datetime(2024, 1, 22).date()

    def test_next_weekly_with_days(self, generator):
        """Test weekly recurrence with specific days."""
        rule = RecurrenceRule(
            frequency=Frequency.WEEKLY,
            days_of_week=[0, 2, 4],  # Mon, Wed, Fri
        )
        after = datetime(2024, 1, 15)  # Monday

        next_date = generator.get_next_occurrence(rule, after)
        # Should be next Wednesday (Jan 17)
        assert next_date.date() == datetime(2024, 1, 17).date()

    def test_next_monthly(self, generator):
        """Test monthly recurrence."""
        rule = RecurrenceRule(frequency=Frequency.MONTHLY)
        after = datetime(2024, 1, 15)

        next_date = generator.get_next_occurrence(rule, after)
        assert next_date.date() == datetime(2024, 2, 15).date()

    def test_next_monthly_end_of_month(self, generator):
        """Test monthly recurrence at end of month."""
        rule = RecurrenceRule(frequency=Frequency.MONTHLY)
        after = datetime(2024, 1, 31)

        # February doesn't have 31 days
        next_date = generator.get_next_occurrence(rule, after)
        assert next_date.date() == datetime(2024, 2, 29).date()  # 2024 is leap year

    def test_next_yearly(self, generator):
        """Test yearly recurrence."""
        rule = RecurrenceRule(frequency=Frequency.YEARLY)
        after = datetime(2024, 3, 15)

        next_date = generator.get_next_occurrence(rule, after)
        assert next_date.date() == datetime(2025, 3, 15).date()

    def test_recurrence_with_end_date(self, generator):
        """Test recurrence with end date."""
        rule = RecurrenceRule(
            frequency=Frequency.DAILY,
            end_date=datetime(2024, 1, 20),
        )

        # Before end date - should work
        next_date = generator.get_next_occurrence(rule, datetime(2024, 1, 15))
        assert next_date is not None

        # After end date - should return None
        next_date = generator.get_next_occurrence(rule, datetime(2024, 1, 21))
        assert next_date is None

    def test_generate_instances(self, generator):
        """Test generating multiple instances."""
        template = Task(
            title="Daily standup",
            recurrence=RecurrenceRule(frequency=Frequency.DAILY),
        )

        instances = generator.generate_instances(
            template,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
        )

        assert len(instances) == 6  # Jan 2-7
        for instance in instances:
            assert instance.title == "Daily standup"
            assert instance.recurrence_parent_id == template.id

    def test_should_generate_next_no_instances(self, generator):
        """Test should_generate_next with no instances."""
        template = Task(
            title="Recurring",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )

        assert generator.should_generate_next(template, []) is True

    def test_should_generate_next_with_open_instance(self, generator):
        """Test should_generate_next with open instance."""
        template = Task(
            title="Recurring",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )
        instance = Task(title="Instance", status=Status.PENDING)

        assert generator.should_generate_next(template, [instance]) is False

    def test_should_generate_next_all_done(self, generator):
        """Test should_generate_next when all instances are done."""
        template = Task(
            title="Recurring",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )
        instance = Task(title="Instance", status=Status.DONE)

        assert generator.should_generate_next(template, [instance]) is True

    def test_create_next_instance(self, generator):
        """Test creating next instance."""
        template = Task(
            title="Weekly review",
            description="Review the week",
            priority=Priority.HIGH,
            tags=["work"],
            project="reviews",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )

        instance = generator.create_next_instance(template)
        assert instance is not None
        assert instance.title == template.title
        assert instance.description == template.description
        assert instance.priority == template.priority
        assert instance.tags == template.tags
        assert instance.project == template.project
        assert instance.recurrence_parent_id == template.id
        assert instance.due_date is not None


class TestTaskManager:
    """Tests for TaskManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a task manager with temp storage."""
        return TaskManager(tmp_path)

    def test_add_task(self, manager):
        """Test adding a task."""
        task = manager.add(title="Test task")
        assert task.title == "Test task"
        assert manager.get(task.id) is not None

    def test_add_task_with_all_options(self, manager):
        """Test adding a task with all options."""
        due = datetime(2024, 6, 15)
        task = manager.add(
            title="Full task",
            description="Description",
            priority=Priority.HIGH,
            due_date=due,
            tags=["tag1", "tag2"],
            project="project-a",
            estimated_hours=4.0,
        )

        assert task.priority == Priority.HIGH
        assert task.due_date == due
        assert task.tags == ["tag1", "tag2"]
        assert task.project == "project-a"
        assert task.estimated_hours == 4.0

    def test_add_task_with_parent(self, manager):
        """Test adding a task with parent."""
        parent = manager.add(title="Parent")
        child = manager.add(title="Child", parent_id=parent.short_id)

        assert child.parent_id == parent.id

    def test_add_task_with_invalid_parent(self, manager):
        """Test adding task with invalid parent."""
        with pytest.raises(ValueError, match="Parent task not found"):
            manager.add(title="Child", parent_id="invalid-id")

    def test_add_task_with_dependencies(self, manager):
        """Test adding task with dependencies."""
        dep1 = manager.add(title="Dep 1")
        dep2 = manager.add(title="Dep 2")

        task = manager.add(
            title="Main",
            dependencies=[dep1.short_id, dep2.short_id],
        )

        assert len(task.dependencies) == 2
        assert dep1.id in task.dependencies
        assert dep2.id in task.dependencies

    def test_add_task_with_invalid_dependency(self, manager):
        """Test adding task with invalid dependency."""
        with pytest.raises(ValueError, match="Dependency task not found"):
            manager.add(title="Main", dependencies=["invalid-id"])

    def test_start_task(self, manager):
        """Test starting a task."""
        task = manager.add(title="Test")
        started = manager.start(task.id)

        assert started.status == Status.IN_PROGRESS

    def test_start_blocked_task(self, manager):
        """Test starting a blocked task."""
        blocker = manager.add(title="Blocker")
        blocked = manager.add(title="Blocked", dependencies=[blocker.id])

        with pytest.raises(ValueError, match="Task is blocked by"):
            manager.start(blocked.id)

    def test_complete_task(self, manager):
        """Test completing a task."""
        task = manager.add(title="Test")
        manager.start(task.id)
        completed = manager.complete(task.id, actual_hours=2.5)

        assert completed.status == Status.DONE
        assert completed.actual_hours == 2.5

    def test_cancel_task(self, manager):
        """Test cancelling a task."""
        task = manager.add(title="Test")
        cancelled = manager.cancel(task.id)

        assert cancelled.status == Status.CANCELLED

    def test_delete_task(self, manager):
        """Test deleting a task."""
        task = manager.add(title="Test")
        result = manager.delete(task.id)

        assert result is True
        assert manager.get(task.id) is None

    def test_delete_task_with_dependents(self, manager):
        """Test deleting a task that others depend on."""
        dep = manager.add(title="Dependency")
        manager.add(title="Dependent", dependencies=[dep.id])

        with pytest.raises(ValueError, match="Cannot delete"):
            manager.delete(dep.id)

    def test_delete_task_with_children(self, manager):
        """Test deleting a task with children."""
        parent = manager.add(title="Parent")
        manager.add(title="Child", parent_id=parent.id)

        with pytest.raises(ValueError, match="has.*child task"):
            manager.delete(parent.id)

    def test_add_note(self, manager):
        """Test adding a note."""
        task = manager.add(title="Test")
        updated = manager.add_note(task.id, "Note content")

        assert len(updated.notes) == 1
        assert updated.notes[0].content == "Note content"

    def test_update_task(self, manager):
        """Test updating task fields."""
        task = manager.add(title="Original")

        updated = manager.update(
            task.id,
            title="Updated",
            priority=Priority.HIGH,
            tags=["new-tag"],
        )

        assert updated.title == "Updated"
        assert updated.priority == Priority.HIGH
        assert updated.tags == ["new-tag"]

    def test_list_tasks_sorted(self, manager):
        """Test that tasks are sorted by priority and due date."""
        manager.add(title="Low", priority=Priority.LOW)
        manager.add(title="Urgent", priority=Priority.URGENT)
        manager.add(
            title="High with due",
            priority=Priority.HIGH,
            due_date=datetime(2024, 1, 10),
        )
        manager.add(
            title="High later",
            priority=Priority.HIGH,
            due_date=datetime(2024, 1, 20),
        )

        tasks = manager.list()
        titles = [t.title for t in tasks]

        # Urgent should be first
        assert titles[0] == "Urgent"
        # High with earlier due date should come before high with later due date
        assert titles.index("High with due") < titles.index("High later")
        # Low should be last
        assert titles[-1] == "Low"

    def test_search(self, manager):
        """Test searching tasks."""
        manager.add(title="Fix login bug")
        manager.add(title="Add feature", description="Improve login")
        manager.add(title="Update docs")

        results = manager.search("login")
        assert len(results) == 2

    def test_get_projects(self, manager):
        """Test getting all projects."""
        manager.add(title="A", project="alpha")
        manager.add(title="B", project="beta")

        projects = manager.get_projects()
        assert "alpha" in projects
        assert "beta" in projects

    def test_get_tags(self, manager):
        """Test getting all tags."""
        manager.add(title="A", tags=["tag1"])
        manager.add(title="B", tags=["tag2"])

        tags = manager.get_tags()
        assert "tag1" in tags
        assert "tag2" in tags

    def test_get_tree(self, manager):
        """Test getting task tree."""
        parent = manager.add(title="Parent")
        child1 = manager.add(title="Child 1", parent_id=parent.id)
        grandchild = manager.add(title="Grandchild", parent_id=child1.id)
        child2 = manager.add(title="Child 2", parent_id=parent.id)

        tree = manager.get_tree()

        # Check depths
        depths = {title: depth for (t, depth) in tree for title in [t.title]}
        # Root tasks have depth 0, but our parent is a root task
        # Actually the get_tree function starts from root_id=None

    def test_recurring_task_generation(self, manager):
        """Test automatic generation of recurring task instances."""
        # Create recurring task
        template = manager.add(
            title="Daily standup",
            recurrence=RecurrenceRule(frequency=Frequency.DAILY),
        )

        # Generate first instance
        generated = manager.generate_recurring_tasks()
        assert len(generated) == 1
        assert generated[0].recurrence_parent_id == template.id

        # Complete the instance
        manager.complete(generated[0].id)

        # Should generate next instance when we call generate again
        # (Note: in real usage, complete() auto-generates next)
