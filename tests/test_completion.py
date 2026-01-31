"""Tests for shell completion functions."""

from unittest.mock import patch

import pytest

from task_butler.cli.completion import (
    complete_open_task_id,
    complete_project_name,
    complete_tag_name,
    complete_task_id,
)
from task_butler.core.task_manager import TaskManager


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path


@pytest.fixture
def manager(storage_dir):
    """Create a TaskManager with temporary storage."""
    return TaskManager(storage_dir)


class TestCompleteTaskId:
    """Tests for complete_task_id function."""

    def test_empty_input_returns_all_tasks(self, manager, storage_dir):
        """Test that empty input returns all tasks."""
        task1 = manager.add(title="Task 1")
        task2 = manager.add(title="Task 2")

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_task_id("")

        assert len(results) == 2
        short_ids = [r[0] for r in results]
        assert task1.short_id in short_ids
        assert task2.short_id in short_ids

    def test_partial_id_filters_results(self, manager, storage_dir):
        """Test that partial ID filters to matching tasks."""
        task1 = manager.add(title="Task 1")
        manager.add(title="Task 2")  # Add second task to ensure filtering works

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            # Use first 3 characters of task1's ID
            prefix = task1.short_id[:3]
            results = complete_task_id(prefix)

        # Should contain task1, may or may not contain task2 depending on IDs
        matching_ids = [r[0] for r in results]
        assert any(task1.short_id in id for id in matching_ids)

    def test_includes_completed_tasks(self, manager, storage_dir):
        """Test that completed tasks are included."""
        task = manager.add(title="Completed task")
        manager.complete(task.id)

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_task_id("")

        assert len(results) == 1
        assert results[0][0] == task.short_id
        assert "Completed task" in results[0][1]

    def test_case_insensitive_matching(self, manager, storage_dir):
        """Test that matching is case-insensitive."""
        task = manager.add(title="Task ABC")

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            prefix = task.short_id[:3].upper()
            results = complete_task_id(prefix)

        assert len(results) >= 1

    def test_returns_empty_on_error(self):
        """Test that errors return empty list instead of raising."""
        with patch("task_butler.cli.completion._get_manager", side_effect=Exception("Test error")):
            results = complete_task_id("")

        assert results == []


class TestCompleteOpenTaskId:
    """Tests for complete_open_task_id function."""

    def test_returns_only_open_tasks(self, manager, storage_dir):
        """Test that only open (pending/in_progress) tasks are returned."""
        pending = manager.add(title="Pending task")
        in_progress = manager.add(title="In progress task")
        manager.start(in_progress.id)
        done = manager.add(title="Done task")
        manager.complete(done.id)
        cancelled = manager.add(title="Cancelled task")
        manager.cancel(cancelled.id)

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_open_task_id("")

        short_ids = [r[0] for r in results]
        assert pending.short_id in short_ids
        assert in_progress.short_id in short_ids
        assert done.short_id not in short_ids
        assert cancelled.short_id not in short_ids

    def test_includes_status_indicator(self, manager, storage_dir):
        """Test that status indicator is included in help text."""
        pending = manager.add(title="Pending task")
        in_progress = manager.add(title="In progress task")
        manager.start(in_progress.id)

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_open_task_id("")

        # Find the results for each task
        pending_result = next(r for r in results if r[0] == pending.short_id)
        in_progress_result = next(r for r in results if r[0] == in_progress.short_id)

        # Check status indicators
        assert pending_result[1].startswith("\u25cb")  # Circle for pending
        assert in_progress_result[1].startswith("\u25d0")  # Half-circle for in_progress

    def test_returns_empty_on_error(self):
        """Test that errors return empty list instead of raising."""
        with patch("task_butler.cli.completion._get_manager", side_effect=Exception("Test error")):
            results = complete_open_task_id("")

        assert results == []


class TestCompleteProjectName:
    """Tests for complete_project_name function."""

    def test_returns_matching_projects(self, manager, storage_dir):
        """Test that matching projects are returned."""
        manager.add(title="Task 1", project="project-alpha")
        manager.add(title="Task 2", project="project-beta")
        manager.add(title="Task 3", project="other-project")

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_project_name("project")

        assert "project-alpha" in results
        assert "project-beta" in results
        assert "other-project" not in results

    def test_empty_input_returns_all_projects(self, manager, storage_dir):
        """Test that empty input returns all projects."""
        manager.add(title="Task 1", project="project-1")
        manager.add(title="Task 2", project="project-2")

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_project_name("")

        assert "project-1" in results
        assert "project-2" in results

    def test_case_insensitive_matching(self, manager, storage_dir):
        """Test that matching is case-insensitive."""
        manager.add(title="Task", project="MyProject")

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_project_name("myp")

        assert "MyProject" in results

    def test_returns_empty_on_error(self):
        """Test that errors return empty list instead of raising."""
        with patch("task_butler.cli.completion._get_manager", side_effect=Exception("Test error")):
            results = complete_project_name("")

        assert results == []


class TestCompleteTagName:
    """Tests for complete_tag_name function."""

    def test_returns_matching_tags(self, manager, storage_dir):
        """Test that matching tags are returned."""
        manager.add(title="Task 1", tags=["work", "important"])
        manager.add(title="Task 2", tags=["work", "urgent"])
        manager.add(title="Task 3", tags=["personal"])

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_tag_name("wo")

        assert "work" in results
        assert "important" not in results
        assert "urgent" not in results
        assert "personal" not in results

    def test_empty_input_returns_all_tags(self, manager, storage_dir):
        """Test that empty input returns all tags."""
        manager.add(title="Task 1", tags=["tag1", "tag2"])
        manager.add(title="Task 2", tags=["tag3"])

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_tag_name("")

        assert "tag1" in results
        assert "tag2" in results
        assert "tag3" in results

    def test_case_insensitive_matching(self, manager, storage_dir):
        """Test that matching is case-insensitive."""
        manager.add(title="Task", tags=["Important"])

        with patch("task_butler.cli.completion._get_manager", return_value=manager):
            results = complete_tag_name("imp")

        assert "Important" in results

    def test_returns_empty_on_error(self):
        """Test that errors return empty list instead of raising."""
        with patch("task_butler.cli.completion._get_manager", side_effect=Exception("Test error")):
            results = complete_tag_name("")

        assert results == []
