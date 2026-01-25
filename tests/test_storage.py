"""Tests for storage layer."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from task_butler.models.task import Task, RecurrenceRule
from task_butler.models.enums import Status, Priority, Frequency
from task_butler.storage.markdown import MarkdownStorage
from task_butler.storage.repository import TaskRepository
from task_butler.storage.obsidian import ObsidianTasksFormat


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


class TestMarkdownStorageHybridMode:
    """Tests for MarkdownStorage hybrid mode."""

    @pytest.fixture
    def storage_hybrid(self, tmp_path):
        """Create a storage instance with hybrid format."""
        return MarkdownStorage(tmp_path, format="hybrid")

    @pytest.fixture
    def storage_frontmatter(self, tmp_path):
        """Create a storage instance with frontmatter format (default)."""
        return MarkdownStorage(tmp_path, format="frontmatter")

    def test_hybrid_mode_includes_obsidian_line(self, storage_hybrid):
        """Test hybrid mode includes Obsidian Tasks line."""
        task = Task(
            title="Test task",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
        )
        path = storage_hybrid.save(task)

        content = path.read_text()

        # Should have frontmatter
        assert "---" in content
        assert "title: Test task" in content

        # Should have Obsidian Tasks line
        assert "- [ ] Test task" in content
        assert "⏫" in content  # High priority emoji
        assert "📅 2025-02-01" in content

    def test_frontmatter_mode_no_obsidian_line(self, storage_frontmatter):
        """Test frontmatter mode does not include Obsidian Tasks line."""
        task = Task(
            title="Test task",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
        )
        path = storage_frontmatter.save(task)

        content = path.read_text()

        # Should have frontmatter
        assert "---" in content
        assert "title: Test task" in content

        # Should NOT have Obsidian Tasks line
        assert "- [ ] Test task" not in content

    def test_hybrid_with_description(self, storage_hybrid):
        """Test hybrid mode with description."""
        task = Task(
            title="Meeting prep",
            description="Prepare slides for the meeting",
            due_date=datetime(2025, 2, 1),
        )
        path = storage_hybrid.save(task)

        content = path.read_text()

        # Obsidian line should come before description
        obsidian_idx = content.find("- [ ] Meeting prep")
        desc_idx = content.find("Prepare slides")

        assert obsidian_idx < desc_idx

    def test_hybrid_with_completed_task(self, storage_hybrid):
        """Test hybrid mode with completed task."""
        task = Task(
            title="Done task",
            status=Status.DONE,
        )
        path = storage_hybrid.save(task)

        content = path.read_text()

        # Should have checked checkbox
        assert "- [x] Done task" in content

    def test_hybrid_with_tags(self, storage_hybrid):
        """Test hybrid mode includes tags."""
        task = Task(
            title="Tagged task",
            tags=["work", "urgent"],
        )
        path = storage_hybrid.save(task)

        content = path.read_text()

        # Tags should be in Obsidian line
        assert "#work" in content
        assert "#urgent" in content

    def test_hybrid_load_preserves_data(self, storage_hybrid):
        """Test loading hybrid format preserves task data."""
        task = Task(
            title="Test task",
            description="A test task",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
            tags=["test"],
        )
        storage_hybrid.save(task)

        loaded = storage_hybrid.load(task.id)

        # Core data should be preserved (loaded from frontmatter)
        assert loaded.title == task.title
        assert loaded.priority == task.priority
        assert loaded.due_date.date() == task.due_date.date()
        assert loaded.tags == task.tags

    def test_hybrid_with_notes(self, storage_hybrid):
        """Test hybrid mode preserves notes."""
        task = Task(title="Task with notes")
        task.add_note("First note")
        task.add_note("Second note")
        storage_hybrid.save(task)

        loaded = storage_hybrid.load(task.id)

        assert len(loaded.notes) == 2
        assert loaded.notes[0].content == "First note"

    def test_hybrid_with_recurrence(self, storage_hybrid):
        """Test hybrid mode with recurring task."""
        task = Task(
            title="Weekly review",
            recurrence=RecurrenceRule(frequency=Frequency.WEEKLY),
        )
        path = storage_hybrid.save(task)

        content = path.read_text()

        # Should have recurrence emoji
        assert "🔁" in content
        assert "every week" in content

    def test_hybrid_multiple_saves_no_duplication(self, storage_hybrid):
        """Test that multiple saves don't duplicate Obsidian Tasks line."""
        task = Task(
            title="Test task",
            priority=Priority.HIGH,
            due_date=datetime(2025, 2, 1),
        )

        # First save
        storage_hybrid.save(task)

        # Load and save again (simulating adding a note)
        loaded = storage_hybrid.load(task.id)
        loaded.add_note("Test note")
        path = storage_hybrid.save(loaded)

        content = path.read_text()

        # Count Obsidian Tasks lines - should be exactly one
        obsidian_line_count = content.count("- [ ] Test task")
        assert obsidian_line_count == 1, f"Expected 1 Obsidian line, found {obsidian_line_count}"

    def test_hybrid_load_strips_obsidian_line_from_description(self, storage_hybrid):
        """Test that loading strips Obsidian Tasks line from description."""
        task = Task(
            title="Test task",
            description="This is the real description",
            due_date=datetime(2025, 2, 1),
        )

        storage_hybrid.save(task)
        loaded = storage_hybrid.load(task.id)

        # Description should not contain Obsidian Tasks line
        assert "- [ ]" not in loaded.description
        assert "This is the real description" in loaded.description

    def test_hybrid_multiple_saves_with_status_change(self, storage_hybrid):
        """Test multiple saves with status change (checkbox updates correctly)."""
        task = Task(
            title="Status change task",
            due_date=datetime(2025, 2, 1),
        )

        # First save (pending)
        storage_hybrid.save(task)

        # Load, change status, save
        loaded = storage_hybrid.load(task.id)
        loaded.complete()
        path = storage_hybrid.save(loaded)

        content = path.read_text()

        # Should have [x] not [ ]
        assert "- [x] Status change task" in content
        assert "- [ ] Status change task" not in content
        # Still only one Obsidian line
        assert content.count("- [x]") == 1

    def test_hybrid_three_consecutive_saves(self, storage_hybrid):
        """Test three consecutive save-load cycles don't accumulate lines."""
        task = Task(
            title="Multi save task",
            due_date=datetime(2025, 2, 1),
        )

        # Save 1
        storage_hybrid.save(task)

        # Load and save 2
        loaded = storage_hybrid.load(task.id)
        loaded.add_note("Note 1")
        storage_hybrid.save(loaded)

        # Load and save 3
        loaded = storage_hybrid.load(task.id)
        loaded.add_note("Note 2")
        path = storage_hybrid.save(loaded)

        content = path.read_text()

        # Should have exactly one Obsidian line
        obsidian_count = content.count("- [ ] Multi save task")
        assert obsidian_count == 1, f"Expected 1, found {obsidian_count}"

        # Notes should still be preserved
        assert "Note 1" in content
        assert "Note 2" in content

    def test_hybrid_empty_description(self, storage_hybrid):
        """Test hybrid mode with empty description."""
        task = Task(
            title="No description task",
            due_date=datetime(2025, 2, 1),
        )

        storage_hybrid.save(task)
        loaded = storage_hybrid.load(task.id)

        # Description should be empty after stripping Obsidian line
        assert loaded.description == ""

        # Save again
        path = storage_hybrid.save(loaded)
        content = path.read_text()

        # Should still have exactly one Obsidian line
        assert content.count("- [ ] No description task") == 1

    def test_hybrid_completed_task_multiple_saves(self, storage_hybrid):
        """Test completed task (- [x]) doesn't duplicate on multiple saves."""
        task = Task(
            title="Completed task",
            status=Status.DONE,
            due_date=datetime(2025, 2, 1),
        )

        # First save
        storage_hybrid.save(task)

        # Load and save again
        loaded = storage_hybrid.load(task.id)
        loaded.add_note("Done note")
        path = storage_hybrid.save(loaded)

        content = path.read_text()

        # Should have exactly one [x] line
        assert content.count("- [x] Completed task") == 1
        assert "- [ ]" not in content

    def test_strip_obsidian_lines_helper(self, storage_hybrid):
        """Test _strip_obsidian_lines helper method directly."""
        # Test with unchecked task
        content1 = "- [ ] Task title\n\nDescription here"
        result1 = storage_hybrid._strip_obsidian_lines(content1)
        assert "- [ ]" not in result1
        assert "Description here" in result1

        # Test with checked task
        content2 = "- [x] Done task\n\nMore content"
        result2 = storage_hybrid._strip_obsidian_lines(content2)
        assert "- [x]" not in result2
        assert "More content" in result2

        # Test with uppercase X
        content3 = "- [X] Also done\n\nContent"
        result3 = storage_hybrid._strip_obsidian_lines(content3)
        assert "- [X]" not in result3

        # Test with no Obsidian line
        content4 = "Just a description"
        result4 = storage_hybrid._strip_obsidian_lines(content4)
        assert result4 == "Just a description"


class TestTaskRepositoryWithFormat:
    """Tests for TaskRepository with format parameter."""

    @pytest.fixture
    def repo_hybrid(self, tmp_path):
        """Create a repository with hybrid format."""
        return TaskRepository(tmp_path, format="hybrid")

    @pytest.fixture
    def repo_frontmatter(self, tmp_path):
        """Create a repository with frontmatter format."""
        return TaskRepository(tmp_path, format="frontmatter")

    def test_repository_hybrid_format(self, repo_hybrid, tmp_path):
        """Test repository creates files in hybrid format."""
        task = Task(title="Hybrid task", due_date=datetime(2025, 2, 1))
        repo_hybrid.create(task)

        # Check file content
        path = tmp_path / f"{task.id}.md"
        content = path.read_text()

        assert "- [ ] Hybrid task" in content
        assert "📅 2025-02-01" in content

    def test_repository_frontmatter_format(self, repo_frontmatter, tmp_path):
        """Test repository creates files in frontmatter format."""
        task = Task(title="Frontmatter task", due_date=datetime(2025, 2, 1))
        repo_frontmatter.create(task)

        # Check file content
        path = tmp_path / f"{task.id}.md"
        content = path.read_text()

        assert "- [ ] Frontmatter task" not in content
        assert "due_date:" in content
