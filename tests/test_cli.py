"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner

from task_butler.cli.main import app
from task_butler.core.task_manager import TaskManager

runner = CliRunner()


@pytest.fixture
def storage_dir(tmp_path):
    """Create a temporary storage directory."""
    return tmp_path


@pytest.fixture
def cli_args(storage_dir):
    """Return common CLI arguments with storage dir."""
    return ["--storage-dir", str(storage_dir)]


class TestAddCommand:
    """Tests for the add command."""

    def test_add_minimal_task(self, cli_args):
        """Test adding a task with minimal options."""
        result = runner.invoke(app, cli_args + ["add", "Test task"])
        assert result.exit_code == 0
        assert "Created task" in result.output
        assert "Test task" in result.output

    def test_add_task_with_priority(self, cli_args):
        """Test adding a task with priority."""
        result = runner.invoke(app, cli_args + ["add", "Important task", "--priority", "high"])
        assert result.exit_code == 0
        assert "Created task" in result.output

    def test_add_task_with_due_date(self, cli_args):
        """Test adding a task with due date."""
        result = runner.invoke(app, cli_args + ["add", "Due task", "--due", "2024-06-15"])
        assert result.exit_code == 0
        assert "Due:" in result.output

    def test_add_task_with_relative_due(self, cli_args):
        """Test adding a task with relative due date."""
        result = runner.invoke(app, cli_args + ["add", "Today task", "--due", "today"])
        assert result.exit_code == 0
        assert "Created task" in result.output

    def test_add_task_with_tags(self, cli_args):
        """Test adding a task with tags."""
        result = runner.invoke(app, cli_args + ["add", "Tagged task", "--tags", "work,important"])
        assert result.exit_code == 0

    def test_add_task_with_project(self, cli_args):
        """Test adding a task with project."""
        result = runner.invoke(app, cli_args + ["add", "Project task", "--project", "my-project"])
        assert result.exit_code == 0
        assert "Project:" in result.output

    def test_add_recurring_task(self, cli_args):
        """Test adding a recurring task."""
        result = runner.invoke(app, cli_args + ["add", "Daily standup", "--recur", "daily"])
        assert result.exit_code == 0
        assert "Recurring:" in result.output

    def test_add_recurring_task_with_interval(self, cli_args):
        """Test adding a recurring task with interval."""
        result = runner.invoke(
            app, cli_args + ["add", "Biweekly review", "--recur", "every 2 weeks"]
        )
        assert result.exit_code == 0
        assert "Recurring:" in result.output


class TestListCommand:
    """Tests for the list command."""

    def test_list_empty(self, cli_args):
        """Test listing when no tasks exist."""
        result = runner.invoke(app, cli_args + ["list"])
        assert result.exit_code == 0
        assert "No tasks found" in result.output

    def test_list_tasks(self, cli_args, storage_dir):
        """Test listing tasks."""
        # Create some tasks first
        manager = TaskManager(storage_dir)
        manager.add(title="Task 1")
        manager.add(title="Task 2")

        result = runner.invoke(app, cli_args + ["list"])
        assert result.exit_code == 0
        assert "Task 1" in result.output
        assert "Task 2" in result.output
        assert "2 task(s)" in result.output

    def test_list_with_table_format(self, cli_args, storage_dir):
        """Test listing tasks in table format."""
        manager = TaskManager(storage_dir)
        manager.add(title="Task 1", project="test")

        result = runner.invoke(app, cli_args + ["list", "--table"])
        assert result.exit_code == 0
        assert "Task 1" in result.output

    def test_list_filter_by_priority(self, cli_args, storage_dir):
        """Test filtering by priority."""
        from task_butler.models.enums import Priority

        manager = TaskManager(storage_dir)
        manager.add(title="Low task", priority=Priority.LOW)
        manager.add(title="High task", priority=Priority.HIGH)

        result = runner.invoke(app, cli_args + ["list", "--priority", "high"])
        assert result.exit_code == 0
        assert "High task" in result.output
        assert "Low task" not in result.output


class TestShowCommand:
    """Tests for the show command."""

    def test_show_task(self, cli_args, storage_dir):
        """Test showing task details."""
        manager = TaskManager(storage_dir)
        task = manager.add(
            title="Test task",
            description="Test description",
        )

        result = runner.invoke(app, cli_args + ["show", task.short_id])
        assert result.exit_code == 0
        assert "Test task" in result.output
        assert "Test description" in result.output

    def test_show_nonexistent_task(self, cli_args):
        """Test showing a task that doesn't exist."""
        result = runner.invoke(app, cli_args + ["show", "invalid-id"])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestStatusCommands:
    """Tests for status-changing commands."""

    def test_start_task(self, cli_args, storage_dir):
        """Test starting a task."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["start", task.short_id])
        assert result.exit_code == 0
        assert "Started" in result.output

    def test_done_task(self, cli_args, storage_dir):
        """Test completing a task."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["done", task.short_id])
        assert result.exit_code == 0
        assert "Completed" in result.output

    def test_done_task_with_hours(self, cli_args, storage_dir):
        """Test completing a task with hours logged."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["done", task.short_id, "--hours", "2.5"])
        assert result.exit_code == 0
        assert "Logged: 2.5h" in result.output

    def test_cancel_task(self, cli_args, storage_dir):
        """Test cancelling a task."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["cancel", task.short_id])
        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_delete_task_with_force(self, cli_args, storage_dir):
        """Test deleting a task with force flag."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["delete", task.short_id, "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output


class TestNoteCommand:
    """Tests for the note command."""

    def test_add_note(self, cli_args, storage_dir):
        """Test adding a note to a task."""
        manager = TaskManager(storage_dir)
        task = manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["note", task.short_id, "This is a note"])
        assert result.exit_code == 0
        assert "Note added" in result.output


class TestSearchCommand:
    """Tests for the search command."""

    def test_search_tasks(self, cli_args, storage_dir):
        """Test searching tasks."""
        manager = TaskManager(storage_dir)
        manager.add(title="Fix login bug")
        manager.add(title="Add logout feature")
        manager.add(title="Update docs")

        result = runner.invoke(app, cli_args + ["search", "log"])
        assert result.exit_code == 0
        assert "login" in result.output.lower() or "logout" in result.output.lower()

    def test_search_no_results(self, cli_args, storage_dir):
        """Test search with no results."""
        manager = TaskManager(storage_dir)
        manager.add(title="Test task")

        result = runner.invoke(app, cli_args + ["search", "nonexistent"])
        assert result.exit_code == 0
        assert "No tasks matching" in result.output


class TestOtherCommands:
    """Tests for other commands."""

    def test_version(self, cli_args):
        """Test version command."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Task Butler" in result.output

    def test_projects_empty(self, cli_args):
        """Test projects command with no projects."""
        result = runner.invoke(app, cli_args + ["projects"])
        assert result.exit_code == 0
        assert "No projects found" in result.output

    def test_projects_list(self, cli_args, storage_dir):
        """Test projects command."""
        manager = TaskManager(storage_dir)
        manager.add(title="Task A", project="project-a")
        manager.add(title="Task B", project="project-b")

        result = runner.invoke(app, cli_args + ["projects"])
        assert result.exit_code == 0
        assert "project-a" in result.output
        assert "project-b" in result.output

    def test_tags_empty(self, cli_args):
        """Test tags command with no tags."""
        result = runner.invoke(app, cli_args + ["tags"])
        assert result.exit_code == 0
        assert "No tags found" in result.output

    def test_tags_list(self, cli_args, storage_dir):
        """Test tags command."""
        manager = TaskManager(storage_dir)
        manager.add(title="Task A", tags=["important", "work"])

        result = runner.invoke(app, cli_args + ["tags"])
        assert result.exit_code == 0
        assert "important" in result.output
        assert "work" in result.output


class TestConfigCommand:
    """Tests for config commands."""

    @pytest.fixture
    def config_setup(self, tmp_path, monkeypatch):
        """Setup config with temporary directory."""
        import task_butler.config
        from task_butler.config import Config

        config_dir = tmp_path / ".task-butler"
        config_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Config, "CONFIG_DIR", config_dir)
        monkeypatch.setattr(Config, "CONFIG_PATH", config_dir / "config.toml")
        # Reset global config
        monkeypatch.setattr(task_butler.config, "_config", None)

        return config_dir

    def test_config_show_empty(self, config_setup):
        """Test config show with no configuration."""
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "No configuration set" in result.output

    def test_config_set_format(self, config_setup):
        """Test config set format."""
        result = runner.invoke(app, ["config", "set", "storage.format", "hybrid"])
        assert result.exit_code == 0
        assert "Set storage.format = hybrid" in result.output

    def test_config_get_format(self, config_setup):
        """Test config get format after setting."""
        # Set first
        runner.invoke(app, ["config", "set", "storage.format", "hybrid"])

        # Reset config to reload from file
        import task_butler.config

        task_butler.config._config = None

        # Get
        result = runner.invoke(app, ["config", "get", "storage.format"])
        assert result.exit_code == 0
        assert "hybrid" in result.output

    def test_config_get_not_set(self, config_setup):
        """Test config get for key not set."""
        result = runner.invoke(app, ["config", "get", "storage.format"])
        assert result.exit_code == 1
        assert "not set" in result.output

    def test_config_set_invalid_format(self, config_setup):
        """Test config set with invalid format value."""
        result = runner.invoke(app, ["config", "set", "storage.format", "invalid"])
        assert result.exit_code == 1
        assert "Invalid format" in result.output

    def test_config_set_invalid_key(self, config_setup):
        """Test config set with invalid key."""
        result = runner.invoke(app, ["config", "set", "invalid.key", "value"])
        assert result.exit_code == 1
        assert "Unknown section" in result.output

    def test_config_show_after_set(self, config_setup):
        """Test config show after setting values."""
        runner.invoke(app, ["config", "set", "storage.format", "hybrid"])

        # Reset config to reload
        import task_butler.config

        task_butler.config._config = None

        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "storage.format" in result.output
        assert "hybrid" in result.output

    def test_config_set_dir(self, config_setup):
        """Test config set storage dir."""
        result = runner.invoke(app, ["config", "set", "storage.dir", "/custom/path"])
        assert result.exit_code == 0
        assert "Set storage.dir = /custom/path" in result.output

    def test_config_init(self, config_setup):
        """Test config init wizard."""
        # Simulate user input: format=2 (hybrid), dir=default
        result = runner.invoke(app, ["config", "init"], input="2\n\n")
        assert result.exit_code == 0
        assert "Configuration saved" in result.output
        assert "hybrid" in result.output

    def test_config_init_with_existing(self, config_setup):
        """Test config init with existing config (cancel)."""
        # Set something first
        runner.invoke(app, ["config", "set", "storage.format", "frontmatter"])

        # Reset config to reload
        import task_butler.config

        task_butler.config._config = None

        # Try init and cancel
        result = runner.invoke(app, ["config", "init"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output
