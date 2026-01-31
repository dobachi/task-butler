"""Markdown file storage for tasks."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import frontmatter

from ..models.enums import Frequency, Priority, Status
from ..models.task import Note, RecurrenceRule, Task


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    """Parse a datetime value that may already be a datetime object.

    The frontmatter library may auto-convert date strings to datetime objects,
    so this function handles both cases.

    Args:
        value: A datetime object, ISO format string, or None

    Returns:
        Parsed datetime or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


class MarkdownStorage:
    """Read and write tasks as Markdown files with YAML frontmatter."""

    # Characters not allowed in filenames (Windows + Unix restrictions)
    INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    # Maximum title length in filename (to avoid path length issues)
    MAX_TITLE_LENGTH = 50

    # Status to Kanban directory key mapping
    STATUS_TO_KANBAN_KEY = {
        Status.PENDING: "backlog",
        Status.IN_PROGRESS: "in_progress",
        Status.DONE: "done",
        Status.CANCELLED: "cancelled",
    }

    def __init__(
        self,
        base_dir: Path,
        format: str = "frontmatter",
        organization: str = "flat",
        kanban_dirs: dict[str, str] | None = None,
    ):
        """Initialize storage with base directory.

        Args:
            base_dir: Directory to store task files
            format: Storage format - "frontmatter" (default) or "hybrid"
                   "hybrid" adds Obsidian Tasks line after frontmatter
            organization: Organization method - "flat" (default) or "kanban"
                         "kanban" uses status-based subdirectories
            kanban_dirs: Custom directory names for Kanban mode
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.format = format
        self.organization = organization
        self.kanban_dirs = kanban_dirs or {
            "backlog": "Backlog",
            "in_progress": "InProgress",
            "done": "Done",
            "cancelled": "Cancelled",
        }

    def _get_status_dir(self, status: Status) -> Path:
        """Get directory for a given status.

        Args:
            status: Task status

        Returns:
            Directory path for the status (base_dir for flat, subdirectory for kanban)
        """
        if self.organization != "kanban":
            return self.base_dir

        kanban_key = self.STATUS_TO_KANBAN_KEY.get(status, "backlog")
        subdir_name = self.kanban_dirs.get(kanban_key, "Backlog")
        subdir = self.base_dir / subdir_name
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir

    def _get_all_search_dirs(self) -> list[Path]:
        """Get all directories to search for tasks.

        Returns:
            List of directories to search
        """
        if self.organization != "kanban":
            return [self.base_dir]

        dirs = [self.base_dir]  # Include base_dir for migration
        for dir_name in self.kanban_dirs.values():
            subdir = self.base_dir / dir_name
            if subdir.exists():
                dirs.append(subdir)
        return dirs

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a title for use in a filename.

        Args:
            title: The task title to sanitize

        Returns:
            A sanitized string safe for use in filenames
        """
        # Replace invalid characters with underscore
        sanitized = self.INVALID_FILENAME_CHARS.sub("_", title)
        # Replace multiple spaces/underscores with single underscore
        sanitized = re.sub(r"[\s_]+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Truncate to max length
        if len(sanitized) > self.MAX_TITLE_LENGTH:
            sanitized = sanitized[: self.MAX_TITLE_LENGTH].rstrip("_")
        # Fallback if empty
        if not sanitized:
            sanitized = "task"
        return sanitized

    def _task_filename(self, task_id: str, title: str) -> str:
        """Generate filename for a task.

        Format: {short_id}_{sanitized_title}.md
        Example: abc123_会議準備.md

        Args:
            task_id: Full task UUID
            title: Task title

        Returns:
            Filename string
        """
        short_id = task_id[:8]
        sanitized_title = self._sanitize_filename(title)
        return f"{short_id}_{sanitized_title}.md"

    def _task_path(self, task_id: str, title: str | None = None) -> Path:
        """Get file path for a task.

        Args:
            task_id: Full task UUID
            title: Task title (required for new format, optional for lookup)

        Returns:
            Path to the task file
        """
        if title:
            return self.base_dir / self._task_filename(task_id, title)
        # Fallback: search for file starting with short_id
        return self._find_task_file(task_id)

    def _find_task_file(self, task_id: str) -> Path:
        """Find a task file by ID.

        Searches for files starting with the task's short ID in all directories.

        Args:
            task_id: Full or short task ID

        Returns:
            Path to the task file (may not exist)
        """
        short_id = task_id[:8]

        # Search all directories (for kanban mode, includes all status dirs)
        for search_dir in self._get_all_search_dirs():
            for path in search_dir.glob(f"{short_id}_*.md"):
                return path
            # Also check for legacy UUID-only format
            legacy_path = search_dir / f"{task_id}.md"
            if legacy_path.exists():
                return legacy_path

        # Return expected path in base_dir (for new files, will be moved on save)
        return self.base_dir / f"{short_id}_task.md"

    def save(self, task: Task) -> Path:
        """Save a task to a Markdown file."""
        # Get the target directory based on status (for kanban mode)
        target_dir = self._get_status_dir(task.status)

        # Get the new filename
        filename = self._task_filename(task.id, task.title)
        new_path = target_dir / filename

        # Check if there's an existing file (might be in different dir or have different name)
        existing_path = self._find_task_file(task.id)
        if existing_path.exists() and existing_path != new_path:
            # Delete old file (title changed or status changed in kanban mode)
            existing_path.unlink()

        path = new_path

        # Build frontmatter metadata
        metadata = {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        }

        if task.due_date:
            metadata["due_date"] = task.due_date.isoformat()
        if task.scheduled_date:
            metadata["scheduled_date"] = task.scheduled_date.isoformat()
        if task.start_date:
            metadata["start_date"] = task.start_date.isoformat()
        if task.completed_at:
            metadata["completed_at"] = task.completed_at.isoformat()
        if task.estimated_hours:
            metadata["estimated_hours"] = task.estimated_hours
        if task.actual_hours:
            metadata["actual_hours"] = task.actual_hours
        if task.tags:
            metadata["tags"] = task.tags
        if task.project:
            metadata["project"] = task.project
        if task.parent_id:
            metadata["parent_id"] = task.parent_id
        if task.dependencies:
            metadata["dependencies"] = task.dependencies
        if task.recurrence:
            metadata["recurrence"] = {
                "frequency": task.recurrence.frequency.value,
                "interval": task.recurrence.interval,
            }
            if task.recurrence.days_of_week:
                metadata["recurrence"]["days_of_week"] = task.recurrence.days_of_week
            if task.recurrence.day_of_month:
                metadata["recurrence"]["day_of_month"] = task.recurrence.day_of_month
            if task.recurrence.end_date:
                metadata["recurrence"]["end_date"] = task.recurrence.end_date.isoformat()
        if task.recurrence_parent_id:
            metadata["recurrence_parent_id"] = task.recurrence_parent_id
        if task.source_file:
            metadata["source_file"] = task.source_file
        if task.source_line:
            metadata["source_line"] = task.source_line

        # Build content
        content_parts = []

        # Hybrid mode: Add Obsidian Tasks line at the beginning
        if self.format == "hybrid":
            from .obsidian import ObsidianTasksFormat

            formatter = ObsidianTasksFormat()
            obsidian_line = formatter.to_obsidian_line(task)
            content_parts.append(obsidian_line)
            content_parts.append("")  # Empty line after Obsidian Tasks line

        # Add source link if available (from import)
        if task.source_file:
            content_parts.append(f"Imported from: [[{task.source_file}]]")
            content_parts.append("")

        if task.description:
            content_parts.append(task.description)

        if task.notes:
            content_parts.append("\n## Notes\n")
            for note in task.notes:
                timestamp = note.created_at.strftime("%Y-%m-%d %H:%M")
                content_parts.append(f"- [{timestamp}] {note.content}")

        content = "\n".join(content_parts)

        # Write file
        post = frontmatter.Post(content, **metadata)
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

        return path

    def load(self, task_id: str) -> Task | None:
        """Load a task from a Markdown file."""
        path = self._find_task_file(task_id)
        if not path.exists():
            return None

        return self.load_from_path(path)

    def load_from_path(self, path: Path) -> Task | None:
        """Load a task from a specific file path."""
        if not path.exists():
            return None

        post = frontmatter.load(path)
        metadata = post.metadata

        # Parse recurrence rule if present
        recurrence = None
        if "recurrence" in metadata:
            rec_data = metadata["recurrence"]
            recurrence = RecurrenceRule(
                frequency=Frequency(rec_data["frequency"]),
                interval=rec_data.get("interval", 1),
                days_of_week=rec_data.get("days_of_week"),
                day_of_month=rec_data.get("day_of_month"),
                end_date=datetime.fromisoformat(rec_data["end_date"])
                if rec_data.get("end_date")
                else None,
            )

        # Parse notes from content
        notes = []
        content = post.content
        description = content

        if "## Notes" in content:
            parts = content.split("## Notes")
            description = parts[0].strip()
            notes_section = parts[1] if len(parts) > 1 else ""

            for line in notes_section.strip().split("\n"):
                line = line.strip()
                if line.startswith("- ["):
                    # Parse note: - [2024-01-01 12:00] content
                    try:
                        timestamp_end = line.index("]")
                        timestamp_str = line[3:timestamp_end]
                        note_content = line[timestamp_end + 2 :]
                        note_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M")
                        notes.append(Note(content=note_content, created_at=note_time))
                    except (ValueError, IndexError):
                        # If parsing fails, just use the line as content
                        notes.append(Note(content=line[2:]))

        # Strip Obsidian Tasks lines from description (they start with "- [ ]" or "- [x]")
        # This prevents duplication when saving in hybrid mode
        description = self._strip_obsidian_lines(description)

        # Strip source link line from description (prevents duplication on save/load cycles)
        description = self._strip_source_line(description)

        # Build task
        task = Task(
            id=metadata["id"],
            title=metadata["title"],
            description=description,
            status=Status(metadata["status"]),
            priority=Priority(metadata["priority"]),
            due_date=_parse_datetime(metadata.get("due_date")),
            scheduled_date=_parse_datetime(metadata.get("scheduled_date")),
            start_date=_parse_datetime(metadata.get("start_date")),
            completed_at=_parse_datetime(metadata.get("completed_at")),
            estimated_hours=metadata.get("estimated_hours"),
            actual_hours=metadata.get("actual_hours"),
            tags=metadata.get("tags", []),
            project=metadata.get("project"),
            parent_id=metadata.get("parent_id"),
            dependencies=metadata.get("dependencies", []),
            recurrence=recurrence,
            recurrence_parent_id=metadata.get("recurrence_parent_id"),
            created_at=_parse_datetime(metadata["created_at"]),
            updated_at=_parse_datetime(metadata["updated_at"]),
            notes=notes,
            source_file=metadata.get("source_file"),
            source_line=metadata.get("source_line"),
        )

        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task file."""
        path = self._find_task_file(task_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[Task]:
        """List all tasks in the storage directory."""
        tasks = []
        seen_ids: set[str] = set()

        for search_dir in self._get_all_search_dirs():
            for path in search_dir.glob("*.md"):
                task = self.load_from_path(path)
                if task and task.id not in seen_ids:
                    tasks.append(task)
                    seen_ids.add(task.id)
        return tasks

    def exists(self, task_id: str) -> bool:
        """Check if a task exists."""
        return self._find_task_file(task_id).exists()

    def _strip_obsidian_lines(self, content: str) -> str:
        """Strip Obsidian Tasks lines from content.

        Removes lines that start with "- [ ]" or "- [x]" (case insensitive for x).
        These are Obsidian Tasks format lines that should not be part of
        the description to avoid duplication when saving in hybrid mode.
        """
        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip Obsidian Tasks lines (checkbox format)
            if stripped.startswith("- [ ]") or stripped.lower().startswith("- [x]"):
                continue
            filtered_lines.append(line)

        # Remove leading/trailing empty lines that might result from stripping
        result = "\n".join(filtered_lines)
        return result.strip()

    def _strip_source_line(self, content: str) -> str:
        """Strip source link line from content.

        Removes lines that start with "Imported from: [[" or "Source: [[".
        This prevents duplication when saving/loading in hybrid mode.
        """
        lines = content.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip source link lines
            if stripped.startswith("Imported from: [[") or stripped.startswith("Source: [["):
                continue
            filtered_lines.append(line)

        result = "\n".join(filtered_lines)
        return result.strip()
