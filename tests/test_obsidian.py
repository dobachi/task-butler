"""Tests for Obsidian Tasks format support."""

from datetime import datetime

import pytest

from task_butler.models.enums import Frequency, Priority, Status
from task_butler.models.task import RecurrenceRule, Task
from task_butler.storage.obsidian import (
    ObsidianTasksFormat,
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

    def test_to_obsidian_line_respects_obsidian_has_created(self, formatter):
        """Test that obsidian_has_created flag controls ➕ output."""
        # Task with obsidian_has_created=True (default) includes ➕
        task_with = Task(title="Task with created", created_at=datetime(2025, 1, 15))
        line_with = formatter.to_obsidian_line(task_with)
        assert "➕ 2025-01-15" in line_with

        # Task with obsidian_has_created=False omits ➕
        task_without = Task(
            title="Task without created",
            created_at=datetime(2025, 1, 15),
            obsidian_has_created=False,
        )
        line_without = formatter.to_obsidian_line(task_without)
        assert "➕" not in line_without

    def test_to_obsidian_line_include_created_override(self, formatter):
        """Test that include_created parameter overrides obsidian_has_created."""
        task = Task(
            title="Test task",
            created_at=datetime(2025, 1, 15),
            obsidian_has_created=True,
        )

        # Override to False
        line = formatter.to_obsidian_line(task, include_created=False)
        assert "➕" not in line

        # Override to True on task with obsidian_has_created=False
        task.obsidian_has_created = False
        line = formatter.to_obsidian_line(task, include_created=True)
        assert "➕ 2025-01-15" in line

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


class TestDirectoryImport:
    """Tests for directory import functionality."""

    def test_collect_files_single_file(self, tmp_path):
        """Test collecting a single file."""
        from task_butler.cli.commands.obsidian import _collect_files

        file = tmp_path / "test.md"
        file.write_text("- [ ] Task")

        files = _collect_files(file, recursive=False, pattern="*.md")
        assert len(files) == 1
        assert files[0] == file

    def test_collect_files_directory(self, tmp_path):
        """Test collecting files from directory."""
        from task_butler.cli.commands.obsidian import _collect_files

        (tmp_path / "file1.md").write_text("- [ ] Task 1")
        (tmp_path / "file2.md").write_text("- [ ] Task 2")
        (tmp_path / "ignored.txt").write_text("Not markdown")

        files = _collect_files(tmp_path, recursive=False, pattern="*.md")
        assert len(files) == 2
        assert all(f.suffix == ".md" for f in files)

    def test_collect_files_recursive(self, tmp_path):
        """Test collecting files recursively."""
        from task_butler.cli.commands.obsidian import _collect_files

        (tmp_path / "root.md").write_text("- [ ] Root task")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub.md").write_text("- [ ] Sub task")

        files = _collect_files(tmp_path, recursive=True, pattern="*.md")
        assert len(files) == 2

    def test_collect_files_not_recursive(self, tmp_path):
        """Test that non-recursive mode ignores subdirectories."""
        from task_butler.cli.commands.obsidian import _collect_files

        (tmp_path / "root.md").write_text("- [ ] Root task")
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "sub.md").write_text("- [ ] Sub task")

        files = _collect_files(tmp_path, recursive=False, pattern="*.md")
        assert len(files) == 1
        assert files[0].name == "root.md"

    def test_collect_files_custom_pattern(self, tmp_path):
        """Test collecting files with custom pattern."""
        from task_butler.cli.commands.obsidian import _collect_files

        (tmp_path / "daily.md").write_text("- [ ] Daily")
        (tmp_path / "daily-2025-01-01.md").write_text("- [ ] Dated")
        (tmp_path / "weekly.md").write_text("- [ ] Weekly")

        files = _collect_files(tmp_path, recursive=False, pattern="daily*.md")
        assert len(files) == 2


class TestImportExcludeStorageDir:
    """Tests for excluding storage directory during import."""

    def test_recursive_import_excludes_storage_dir(self, tmp_path):
        """Test that recursive import excludes the storage directory."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup: Vault with storage dir inside
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()

        storage = vault / "Tasks"
        storage.mkdir()

        # Create a task file in storage (should be excluded)
        (storage / "abc12345_Existing.md").write_text(
            "---\nid: abc12345\ntitle: Existing\nstatus: pending\n---\n- [ ] Existing\n"
        )

        # Create a note with task (should be imported)
        (vault / "notes.md").write_text("- [ ] New task 📅 2026-02-01\n")

        # Import with exclude_dir
        files = _collect_files(vault, recursive=True, pattern="*.md", exclude_dir=storage)

        # Assert: Only notes.md is collected
        assert len(files) == 1
        assert files[0].name == "notes.md"

    def test_recursive_import_without_exclude_dir(self, tmp_path):
        """Test that recursive import includes storage dir when exclude_dir is None."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup: Vault with storage dir inside
        vault = tmp_path / "vault"
        vault.mkdir()

        storage = vault / "Tasks"
        storage.mkdir()

        # Create files
        (storage / "task.md").write_text("- [ ] Task in storage")
        (vault / "notes.md").write_text("- [ ] Notes")

        # Import without exclude_dir
        files = _collect_files(vault, recursive=True, pattern="*.md", exclude_dir=None)

        # Assert: Both files are collected
        assert len(files) == 2
        names = {f.name for f in files}
        assert "notes.md" in names
        assert "task.md" in names

    def test_exclude_dir_nested_files(self, tmp_path):
        """Test that nested files in storage directory are also excluded."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup: Vault with nested storage structure
        vault = tmp_path / "vault"
        vault.mkdir()

        storage = vault / "Tasks"
        storage.mkdir()
        nested = storage / "archive"
        nested.mkdir()

        # Create files at various levels
        (storage / "task1.md").write_text("- [ ] Task 1")
        (nested / "archived.md").write_text("- [ ] Archived")
        (vault / "notes.md").write_text("- [ ] Notes")
        (vault / "daily").mkdir()
        (vault / "daily" / "2025-01-01.md").write_text("- [ ] Daily note")

        # Import with exclude_dir
        files = _collect_files(vault, recursive=True, pattern="*.md", exclude_dir=storage)

        # Assert: Only files outside storage are collected
        assert len(files) == 2
        names = {f.name for f in files}
        assert "notes.md" in names
        assert "2025-01-01.md" in names
        assert "task1.md" not in names
        assert "archived.md" not in names

    def test_exclude_dir_not_under_path(self, tmp_path):
        """Test that exclude_dir has no effect when not under the import path."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup: Two separate directories
        import_path = tmp_path / "import"
        import_path.mkdir()
        storage = tmp_path / "storage"
        storage.mkdir()

        # Create files
        (import_path / "notes.md").write_text("- [ ] Notes")
        (storage / "task.md").write_text("- [ ] Task")

        # Import with exclude_dir pointing to separate directory
        files = _collect_files(import_path, recursive=True, pattern="*.md", exclude_dir=storage)

        # Assert: Import path files are collected (storage is separate anyway)
        assert len(files) == 1
        assert files[0].name == "notes.md"

    def test_exclude_dir_single_file_import(self, tmp_path):
        """Test that exclude_dir has no effect when importing a single file."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup
        vault = tmp_path / "vault"
        vault.mkdir()
        storage = vault / "Tasks"
        storage.mkdir()

        file = vault / "notes.md"
        file.write_text("- [ ] Notes")

        # Import single file with exclude_dir (should have no effect)
        files = _collect_files(file, recursive=False, pattern="*.md", exclude_dir=storage)

        # Assert: Single file is returned
        assert len(files) == 1
        assert files[0] == file

    def test_exclude_nonexistent_dir(self, tmp_path):
        """Test that nonexistent exclude_dir is safely ignored."""
        from task_butler.cli.commands.obsidian import _collect_files

        # Setup
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "notes.md").write_text("- [ ] Notes")
        (vault / "other.md").write_text("- [ ] Other")

        nonexistent_storage = vault / "NonExistent"  # Does not exist

        # Import with nonexistent exclude_dir
        files = _collect_files(
            vault, recursive=True, pattern="*.md", exclude_dir=nonexistent_storage
        )

        # Assert: All files are collected (nonexistent dir is ignored)
        assert len(files) == 2


class TestVaultRootDetection:
    """Tests for Obsidian vault root detection."""

    def test_find_vault_root_with_obsidian_dir(self, tmp_path):
        """Test finding vault root when .obsidian directory exists."""
        from task_butler.cli.commands.obsidian import find_vault_root

        vault = tmp_path / "my_vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        daily = vault / "daily"
        daily.mkdir()

        # Should find vault root from subdirectory
        result = find_vault_root(daily)
        assert result == vault

    def test_find_vault_root_from_file(self, tmp_path):
        """Test finding vault root from a file path."""
        from task_butler.cli.commands.obsidian import find_vault_root

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        file = vault / "note.md"
        file.write_text("content")

        result = find_vault_root(file)
        assert result == vault

    def test_find_vault_root_not_found(self, tmp_path):
        """Test when no vault root exists."""
        from task_butler.cli.commands.obsidian import find_vault_root

        no_vault = tmp_path / "no_vault"
        no_vault.mkdir()

        result = find_vault_root(no_vault)
        assert result is None


class TestWikiLinkGeneration:
    """Tests for wiki link generation."""

    def test_generate_wiki_link_basic(self, tmp_path):
        """Test generating a basic wiki link."""
        from task_butler.cli.commands.obsidian import (
            LinkFormat,
            generate_wiki_link,
        )

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        storage = vault / "Tasks"
        storage.mkdir()

        task = Task(id="12345678-abcd-1234-abcd-1234567890ab", title="My Task")
        link = generate_wiki_link(task, storage, vault, LinkFormat.WIKI)

        assert link == "[[Tasks/12345678_My_Task|My Task]]"

    def test_generate_wiki_link_embed(self, tmp_path):
        """Test generating an embed link."""
        from task_butler.cli.commands.obsidian import (
            LinkFormat,
            generate_wiki_link,
        )

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        storage = vault / "Tasks"
        storage.mkdir()

        task = Task(id="12345678-abcd-1234-abcd-1234567890ab", title="My Task")
        link = generate_wiki_link(task, storage, vault, LinkFormat.EMBED)

        assert link == "![[Tasks/12345678_My_Task|My Task]]"

    def test_generate_wiki_link_outside_vault(self, tmp_path):
        """Test generating link when storage is outside vault."""
        from task_butler.cli.commands.obsidian import (
            LinkFormat,
            generate_wiki_link,
        )

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        storage = tmp_path / "external_storage"
        storage.mkdir()

        task = Task(id="12345678-abcd-1234-abcd-1234567890ab", title="My Task")
        link = generate_wiki_link(task, storage, vault, LinkFormat.WIKI)

        # Should use absolute path (won't work in Obsidian but shouldn't crash)
        assert "My Task" in link

    def test_generate_wiki_link_kanban_mode(self, tmp_path):
        """Test generating link with Kanban organization mode."""
        from task_butler.cli.commands.obsidian import (
            LinkFormat,
            generate_wiki_link,
        )
        from task_butler.models.enums import Status

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        storage = vault / "Tasks"
        storage.mkdir()

        # Test PENDING status -> Backlog directory
        task_pending = Task(
            id="11111111-aaaa-1111-aaaa-111111111111",
            title="Pending Task",
            status=Status.PENDING,
        )
        link_pending = generate_wiki_link(
            task_pending, storage, vault, LinkFormat.WIKI, organization="kanban"
        )
        assert link_pending == "[[Tasks/Backlog/11111111_Pending_Task|Pending Task]]"

        # Test DONE status -> Done directory
        task_done = Task(
            id="22222222-bbbb-2222-bbbb-222222222222",
            title="Done Task",
            status=Status.DONE,
        )
        link_done = generate_wiki_link(
            task_done, storage, vault, LinkFormat.WIKI, organization="kanban"
        )
        assert link_done == "[[Tasks/Done/22222222_Done_Task|Done Task]]"

        # Test with custom kanban dirs
        custom_dirs = {"backlog": "Todo", "done": "Completed"}
        link_custom = generate_wiki_link(
            task_pending, storage, vault, LinkFormat.WIKI, organization="kanban", kanban_dirs=custom_dirs
        )
        assert link_custom == "[[Tasks/Todo/11111111_Pending_Task|Pending Task]]"


class TestImportDuplicateHandling:
    """Tests for import duplicate handling."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a task manager with temp storage."""
        from task_butler.core.task_manager import TaskManager

        return TaskManager(tmp_path / "storage")

    @pytest.fixture
    def obsidian_file(self, tmp_path):
        """Create a test obsidian file."""
        file = tmp_path / "tasks.md"
        file.write_text("""# Tasks
- [ ] New task 📅 2025-02-01
- [ ] Duplicate task 📅 2025-02-15
""")
        return file

    def test_import_skip_duplicates(self, manager, obsidian_file):
        """Test that duplicates are skipped by default."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create existing task
        manager.add(title="Duplicate task", due_date=datetime(2025, 2, 15))

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            obsidian_file,
            manager,
            formatter,
            DuplicateAction.SKIP,
            dry_run=False,
            global_action=global_action,
        )

        assert len(imported) == 1  # Only "New task" imported
        assert len(skipped) == 1  # "Duplicate task" skipped
        assert skipped[0][0].title == "Duplicate task"
        assert len(task_infos) == 1  # Only imported task has info

    def test_import_update_duplicates(self, manager, obsidian_file, tmp_path):
        """Test that duplicates are updated with --update."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.models.enums import Priority
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create existing task with different priority
        existing = manager.add(
            title="Duplicate task",
            due_date=datetime(2025, 2, 15),
            priority=Priority.LOW,
        )

        # Create file with HIGH priority task
        file = tmp_path / "update_test.md"
        file.write_text("- [ ] Duplicate task ⏫ 📅 2025-02-15")

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            file,
            manager,
            formatter,
            DuplicateAction.UPDATE,
            dry_run=False,
            global_action=global_action,
        )

        assert len(imported) == 0
        assert len(updated) == 1
        assert len(task_infos) == 1  # Updated task has info

        # Check that priority was updated
        refreshed = manager.get(existing.id)
        assert refreshed.priority == Priority.HIGH

    def test_import_force_duplicates(self, manager, obsidian_file):
        """Test that duplicates are created with --force."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create existing task
        manager.add(title="Duplicate task", due_date=datetime(2025, 2, 15))

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            obsidian_file,
            manager,
            formatter,
            DuplicateAction.FORCE,
            dry_run=False,
            global_action=global_action,
        )

        assert len(imported) == 2  # Both tasks created
        assert len(skipped) == 0
        assert len(task_infos) == 2  # Both have info

        # Should have 3 total tasks now (1 existing + 2 new)
        all_tasks = manager.list(include_done=True)
        assert len(all_tasks) == 3

    def test_import_dry_run(self, manager, obsidian_file):
        """Test that dry run doesn't create tasks."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            obsidian_file,
            manager,
            formatter,
            DuplicateAction.SKIP,
            dry_run=True,
            global_action=global_action,
        )

        # Should return parsed tasks but not actually create them
        assert len(imported) == 2

        # No tasks should exist in storage
        all_tasks = manager.list(include_done=True)
        assert len(all_tasks) == 0


class TestLinkReplacement:
    """Tests for link replacement functionality."""

    @pytest.fixture
    def vault(self, tmp_path):
        """Create a mock Obsidian vault."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        return vault

    @pytest.fixture
    def manager(self, vault):
        """Create a task manager with storage inside vault."""
        from task_butler.core.task_manager import TaskManager

        storage = vault / "Tasks"
        return TaskManager(storage)

    def test_import_with_source_tracking(self, vault, manager):
        """Test that source file and line are tracked during import."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create test file
        daily = vault / "daily"
        daily.mkdir()
        file = daily / "2025-01-25.md"
        file.write_text("- [ ] Task from daily note 📅 2025-02-01")

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            file,
            manager,
            formatter,
            DuplicateAction.SKIP,
            dry_run=False,
            global_action=global_action,
            vault_root=vault,
            source_file_relative="daily/2025-01-25.md",
        )

        assert len(imported) == 1
        task = imported[0]
        assert task.source_file == "daily/2025-01-25.md"
        assert task.source_line == 1

    def test_replace_lines_with_links(self, vault, manager):
        """Test replacing task lines with wiki links."""
        from task_butler.cli.commands.obsidian import (
            ImportedTaskInfo,
            LinkFormat,
            _replace_lines_with_links,
        )

        storage = vault / "Tasks"
        storage.mkdir(exist_ok=True)

        # Create test file
        file = vault / "test.md"
        file.write_text("""# Tasks
- [ ] First task
- [ ] Second task
Some other content
""")

        task1 = Task(id="11111111-aaaa-1111-aaaa-111111111111", title="First task")
        task2 = Task(id="22222222-bbbb-2222-bbbb-222222222222", title="Second task")

        task_infos = [
            ImportedTaskInfo(task=task1, line_number=2, original_line="- [ ] First task"),
            ImportedTaskInfo(task=task2, line_number=3, original_line="- [ ] Second task"),
        ]

        _replace_lines_with_links(file, task_infos, storage, vault, LinkFormat.WIKI)

        content = file.read_text()
        assert "[[Tasks/11111111_First_task|First task]]" in content
        assert "[[Tasks/22222222_Second_task|Second task]]" in content
        assert "# Tasks" in content
        assert "Some other content" in content

    def test_replace_lines_preserves_indentation(self, vault, manager):
        """Test that link replacement preserves leading whitespace."""
        from task_butler.cli.commands.obsidian import (
            ImportedTaskInfo,
            LinkFormat,
            _replace_lines_with_links,
        )

        storage = vault / "Tasks"
        storage.mkdir(exist_ok=True)

        # Create test file with indented task
        file = vault / "test.md"
        file.write_text("""# Tasks
    - [ ] Indented task
""")

        task = Task(id="11111111-aaaa-1111-aaaa-111111111111", title="Indented task")
        task_infos = [
            ImportedTaskInfo(task=task, line_number=2, original_line="    - [ ] Indented task"),
        ]

        _replace_lines_with_links(file, task_infos, storage, vault, LinkFormat.WIKI)

        content = file.read_text()
        lines = content.split("\n")
        # Should preserve 4-space indentation
        assert lines[1].startswith("    - [[")

    def test_replace_lines_with_embed_format(self, vault, manager):
        """Test replacing with embed format (![[...]])."""
        from task_butler.cli.commands.obsidian import (
            ImportedTaskInfo,
            LinkFormat,
            _replace_lines_with_links,
        )

        storage = vault / "Tasks"
        storage.mkdir(exist_ok=True)

        file = vault / "test.md"
        file.write_text("- [ ] Task to embed")

        task = Task(id="11111111-aaaa-1111-aaaa-111111111111", title="Task to embed")
        task_infos = [
            ImportedTaskInfo(task=task, line_number=1, original_line="- [ ] Task to embed"),
        ]

        _replace_lines_with_links(file, task_infos, storage, vault, LinkFormat.EMBED)

        content = file.read_text()
        assert "![[Tasks/11111111_Task_to_embed|Task to embed]]" in content

    def test_source_file_loaded_from_storage(self, vault, manager):
        """Test that source_file is correctly loaded from storage."""
        # Create a task with source tracking
        task = manager.add(title="Test task")
        task.source_file = "daily/2025-01-25.md"
        task.source_line = 5
        manager.repository.update(task)

        # Reload task and verify source tracking is preserved
        loaded = manager.get(task.id)
        assert loaded.source_file == "daily/2025-01-25.md"
        assert loaded.source_line == 5


class TestObsidianHasCreated:
    """Tests for obsidian_has_created field handling."""

    @pytest.fixture
    def vault(self, tmp_path):
        """Create a mock Obsidian vault."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()
        return vault

    @pytest.fixture
    def manager(self, vault):
        """Create a task manager with storage inside vault."""
        from task_butler.core.task_manager import TaskManager

        storage = vault / "Tasks"
        return TaskManager(storage)

    def test_import_task_without_created_sets_flag_false(self, vault, manager):
        """Test that importing a task without ➕ sets obsidian_has_created=False."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create file WITHOUT ➕
        file = vault / "test.md"
        file.write_text("- [ ] Task without created 📅 2026-02-01 #work")

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            file,
            manager,
            formatter,
            DuplicateAction.SKIP,
            dry_run=False,
            global_action=global_action,
            vault_root=vault,
            source_file_relative="test.md",
        )

        assert len(imported) == 1
        task = imported[0]
        assert task.obsidian_has_created is False

        # Verify format output doesn't include ➕
        line = formatter.to_obsidian_line(task)
        assert "➕" not in line

    def test_import_task_with_created_sets_flag_true(self, vault, manager):
        """Test that importing a task with ➕ sets obsidian_has_created=True."""
        from task_butler.cli.commands.obsidian import (
            DuplicateAction,
            _import_single_file,
        )
        from task_butler.storage.obsidian import ObsidianTasksFormat

        # Create file WITH ➕
        file = vault / "test.md"
        file.write_text("- [ ] Task with created 📅 2026-02-01 ➕ 2026-01-15 #work")

        formatter = ObsidianTasksFormat()
        global_action = {}

        imported, updated, skipped, errors, task_infos = _import_single_file(
            file,
            manager,
            formatter,
            DuplicateAction.SKIP,
            dry_run=False,
            global_action=global_action,
            vault_root=vault,
            source_file_relative="test.md",
        )

        assert len(imported) == 1
        task = imported[0]
        assert task.obsidian_has_created is True
        assert task.created_at == datetime(2026, 1, 15)

        # Verify format output includes ➕
        line = formatter.to_obsidian_line(task)
        assert "➕ 2026-01-15" in line

    def test_obsidian_has_created_persisted_in_storage(self, vault, manager):
        """Test that obsidian_has_created is persisted and loaded from storage."""
        # Create task with obsidian_has_created=False
        task = manager.add(title="Test task")
        task.obsidian_has_created = False
        manager.repository.update(task)

        # Reload task
        loaded = manager.get(task.id)
        assert loaded.obsidian_has_created is False

        # Create another task with default (True)
        task2 = manager.add(title="Test task 2")
        manager.repository.update(task2)

        loaded2 = manager.get(task2.id)
        assert loaded2.obsidian_has_created is True

    def test_hybrid_format_respects_obsidian_has_created(self, tmp_path):
        """Test that hybrid format respects obsidian_has_created when saving."""
        from task_butler.storage.markdown import MarkdownStorage
        from task_butler.storage.obsidian import ObsidianTasksFormat

        storage = MarkdownStorage(tmp_path, format="hybrid")
        formatter = ObsidianTasksFormat()

        # Create task without created flag
        task = Task(
            title="Test task",
            due_date=datetime(2026, 2, 1),
            created_at=datetime(2026, 1, 15),
            obsidian_has_created=False,
        )
        path = storage.save(task)

        # Read file content directly
        content = path.read_text()

        # The Obsidian line should NOT contain ➕
        assert "- [ ] Test task" in content
        assert "📅 2026-02-01" in content
        assert "➕" not in content
