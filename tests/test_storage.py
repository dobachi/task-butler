"""Tests for storage layer."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from task_butler.models.task import Task, RecurrenceRule
from task_butler.models.enums import Status, Priority, Frequency
from task_butler.storage.markdown import MarkdownStorage
from task_butler.storage.repository import TaskRepository


class TestMarkdownStorage:
    """Tests for MarkdownStorage."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create a storage instance with temp directory."""
        return MarkdownStorage(tmp_path)

    def test_save_minimal_task(self, storage):
        """Test saving a minimal task."""
        task = Task(title="Test task")
        path = storage.save(task)

        assert path.exists()
        assert path.suffix == ".md"
        assert task.id in path.name

    def test_save_and_load_task(self, storage):
        """Test saving and loading a task."""
        task = Task(
            title="Test task",
            description="Test description",
            priority=Priority.HIGH,
            tags=["tag1", "tag2"],
            project="test-project",
        )
        storage.save(task)

        loaded = storage.load(task.id)
        assert loaded is not None
        assert loaded.id == task.id
        assert loaded.title == task.title
        assert loaded.description == task.description
        assert loaded.priority == Priority.HIGH
        assert loaded.tags == ["tag1", "tag2"]
        assert loaded.project == "test-project"

    def test_save_task_with_due_date(self, storage):
        """Test saving task with due date."""
        due = datetime(2024, 6, 15, 14, 30)
        task = Task(title="Due task", due_date=due)
        storage.save(task)

        loaded = storage.load(task.id)
        assert loaded.due_date is not None
        assert loaded.due_date.year == 2024
        assert loaded.due_date.month == 6
        assert loaded.due_date.day == 15

    def test_save_task_with_recurrence(self, storage):
        """Test saving task with recurrence rule."""
        task = Task(
            title="Recurring task",
            recurrence=RecurrenceRule(
                frequency=Frequency.WEEKLY,
                interval=2,
                days_of_week=[0, 2, 4],
            ),
        )
        storage.save(task)

        loaded = storage.load(task.id)
        assert loaded.recurrence is not None
        assert loaded.recurrence.frequency == Frequency.WEEKLY
        assert loaded.recurrence.interval == 2
        assert loaded.recurrence.days_of_week == [0, 2, 4]

    def test_save_task_with_notes(self, storage):
        """Test saving task with notes."""
        task = Task(title="Task with notes")
        task.add_note("Note 1")
        task.add_note("Note 2")
        storage.save(task)

        loaded = storage.load(task.id)
        assert len(loaded.notes) == 2
        assert loaded.notes[0].content == "Note 1"
        assert loaded.notes[1].content == "Note 2"

    def test_load_nonexistent_task(self, storage):
        """Test loading a task that doesn't exist."""
        loaded = storage.load("nonexistent-id")
        assert loaded is None

    def test_delete_task(self, storage):
        """Test deleting a task."""
        task = Task(title="To delete")
        storage.save(task)
        assert storage.exists(task.id)

        result = storage.delete(task.id)
        assert result is True
        assert not storage.exists(task.id)

    def test_delete_nonexistent_task(self, storage):
        """Test deleting a task that doesn't exist."""
        result = storage.delete("nonexistent-id")
        assert result is False

    def test_list_all(self, storage):
        """Test listing all tasks."""
        task1 = Task(title="Task 1")
        task2 = Task(title="Task 2")
        task3 = Task(title="Task 3")

        storage.save(task1)
        storage.save(task2)
        storage.save(task3)

        tasks = storage.list_all()
        assert len(tasks) == 3

        titles = [t.title for t in tasks]
        assert "Task 1" in titles
        assert "Task 2" in titles
        assert "Task 3" in titles


class TestTaskRepository:
    """Tests for TaskRepository."""

    @pytest.fixture
    def repo(self, tmp_path):
        """Create a repository instance with temp directory."""
        return TaskRepository(tmp_path)

    def test_create_task(self, repo):
        """Test creating a task."""
        task = Task(title="New task")
        created = repo.create(task)

        assert created.id == task.id
        assert repo.get(task.id) is not None

    def test_get_by_short_id(self, repo):
        """Test getting a task by short ID."""
        task = Task(title="Test")
        repo.create(task)

        # Should find by short ID (first 8 chars)
        found = repo.get(task.short_id)
        assert found is not None
        assert found.id == task.id

    def test_update_task(self, repo):
        """Test updating a task."""
        task = Task(title="Original")
        repo.create(task)

        task.title = "Updated"
        repo.update(task)

        loaded = repo.get(task.id)
        assert loaded.title == "Updated"

    def test_delete_task(self, repo):
        """Test deleting a task."""
        task = Task(title="To delete")
        repo.create(task)

        result = repo.delete(task.id)
        assert result is True
        assert repo.get(task.id) is None

    def test_list_filter_by_status(self, repo):
        """Test filtering tasks by status."""
        t1 = Task(title="Pending", status=Status.PENDING)
        t2 = Task(title="Done", status=Status.DONE)
        t3 = Task(title="In Progress", status=Status.IN_PROGRESS)

        repo.create(t1)
        repo.create(t2)
        repo.create(t3)

        pending = repo.list_all(status=Status.PENDING)
        assert len(pending) == 1
        assert pending[0].title == "Pending"

    def test_list_filter_by_priority(self, repo):
        """Test filtering tasks by priority."""
        t1 = Task(title="Low", priority=Priority.LOW)
        t2 = Task(title="High", priority=Priority.HIGH)

        repo.create(t1)
        repo.create(t2)

        high = repo.list_all(priority=Priority.HIGH, include_done=True)
        assert len(high) == 1
        assert high[0].title == "High"

    def test_list_filter_by_project(self, repo):
        """Test filtering tasks by project."""
        t1 = Task(title="Project A", project="a")
        t2 = Task(title="Project B", project="b")

        repo.create(t1)
        repo.create(t2)

        project_a = repo.list_all(project="a")
        assert len(project_a) == 1
        assert project_a[0].title == "Project A"

    def test_list_filter_by_tag(self, repo):
        """Test filtering tasks by tag."""
        t1 = Task(title="Tagged", tags=["important", "work"])
        t2 = Task(title="Not tagged", tags=["personal"])

        repo.create(t1)
        repo.create(t2)

        important = repo.list_all(tag="important")
        assert len(important) == 1
        assert important[0].title == "Tagged"

    def test_list_exclude_done(self, repo):
        """Test excluding done tasks by default."""
        t1 = Task(title="Pending", status=Status.PENDING)
        t2 = Task(title="Done", status=Status.DONE)

        repo.create(t1)
        repo.create(t2)

        # By default, done tasks are excluded
        tasks = repo.list_all()
        assert len(tasks) == 1
        assert tasks[0].title == "Pending"

        # Include done
        all_tasks = repo.list_all(include_done=True)
        assert len(all_tasks) == 2

    def test_get_children(self, repo):
        """Test getting child tasks."""
        parent = Task(title="Parent")
        repo.create(parent)

        child1 = Task(title="Child 1", parent_id=parent.id)
        child2 = Task(title="Child 2", parent_id=parent.id)
        repo.create(child1)
        repo.create(child2)

        children = repo.get_children(parent.id)
        assert len(children) == 2

    def test_get_dependents(self, repo):
        """Test getting dependent tasks."""
        dep = Task(title="Dependency")
        repo.create(dep)

        dependent = Task(title="Dependent", dependencies=[dep.id])
        repo.create(dependent)

        dependents = repo.get_dependents(dep.id)
        assert len(dependents) == 1
        assert dependents[0].title == "Dependent"

    def test_get_blocking_tasks(self, repo):
        """Test getting blocking tasks."""
        blocker = Task(title="Blocker", status=Status.PENDING)
        done = Task(title="Done blocker", status=Status.DONE)
        repo.create(blocker)
        repo.create(done)

        task = Task(title="Blocked", dependencies=[blocker.id, done.id])
        repo.create(task)

        blocking = repo.get_blocking_tasks(task.id)
        assert len(blocking) == 1
        assert blocking[0].title == "Blocker"

    def test_can_start(self, repo):
        """Test checking if task can start."""
        blocker = Task(title="Blocker", status=Status.PENDING)
        repo.create(blocker)

        blocked = Task(title="Blocked", dependencies=[blocker.id])
        repo.create(blocked)

        assert repo.can_start(blocked.id) is False

        # Complete the blocker
        blocker.complete()
        repo.update(blocker)

        assert repo.can_start(blocked.id) is True

    def test_get_projects(self, repo):
        """Test getting all projects."""
        repo.create(Task(title="A", project="alpha"))
        repo.create(Task(title="B", project="beta"))
        repo.create(Task(title="C", project="alpha"))

        projects = repo.get_projects()
        assert len(projects) == 2
        assert "alpha" in projects
        assert "beta" in projects

    def test_get_tags(self, repo):
        """Test getting all tags."""
        repo.create(Task(title="A", tags=["tag1", "tag2"]))
        repo.create(Task(title="B", tags=["tag2", "tag3"]))

        tags = repo.get_tags()
        assert len(tags) == 3
        assert "tag1" in tags
        assert "tag2" in tags
        assert "tag3" in tags

    def test_search(self, repo):
        """Test searching tasks."""
        repo.create(Task(title="Fix bug in login"))
        repo.create(Task(title="Add feature", description="Login improvements"))
        repo.create(Task(title="Update docs"))

        results = repo.search("login")
        assert len(results) == 2

        titles = [t.title for t in results]
        assert "Fix bug in login" in titles
        assert "Add feature" in titles
