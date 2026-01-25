"""Markdown file storage for tasks."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import frontmatter

from ..models.enums import Frequency, Priority, Status
from ..models.task import Note, RecurrenceRule, Task


class MarkdownStorage:
    """Read and write tasks as Markdown files with YAML frontmatter."""

    # Characters not allowed in filenames (Windows + Unix restrictions)
    INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    # Maximum title length in filename (to avoid path length issues)
    MAX_TITLE_LENGTH = 50

    def __init__(self, base_dir: Path, format: str = "frontmatter"):
        """Initialize storage with base directory.

        Args:
            base_dir: Directory to store task files
            format: Storage format - "frontmatter" (default) or "hybrid"
                   "hybrid" adds Obsidian Tasks line after frontmatter
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.format = format

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

        Searches for files starting with the task's short ID.

        Args:
            task_id: Full or short task ID

        Returns:
            Path to the task file (may not exist)
        """
        short_id = task_id[:8]
        # Search for existing file
        for path in self.base_dir.glob(f"{short_id}_*.md"):
            return path
        # Also check for legacy UUID-only format
        legacy_path = self.base_dir / f"{task_id}.md"
        if legacy_path.exists():
            return legacy_path
        # Return expected path (for new files)
        return self.base_dir / f"{short_id}_task.md"

    def save(self, task: Task) -> Path:
        """Save a task to a Markdown file."""
        # Get the new path based on current title
        new_path = self._task_path(task.id, task.title)

        # Check if there's an existing file with different name (title changed)
        existing_path = self._find_task_file(task.id)
        if existing_path.exists() and existing_path != new_path:
            # Delete old file (title changed)
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

        # Build content
        content_parts = []

        # Hybrid mode: Add Obsidian Tasks line at the beginning
        if self.format == "hybrid":
            from .obsidian import ObsidianTasksFormat

            formatter = ObsidianTasksFormat()
            obsidian_line = formatter.to_obsidian_line(task)
            content_parts.append(obsidian_line)
            content_parts.append("")  # Empty line after Obsidian Tasks line

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

        # Build task
        task = Task(
            id=metadata["id"],
            title=metadata["title"],
            description=description,
            status=Status(metadata["status"]),
            priority=Priority(metadata["priority"]),
            due_date=datetime.fromisoformat(metadata["due_date"])
            if metadata.get("due_date")
            else None,
            scheduled_date=datetime.fromisoformat(metadata["scheduled_date"])
            if metadata.get("scheduled_date")
            else None,
            start_date=datetime.fromisoformat(metadata["start_date"])
            if metadata.get("start_date")
            else None,
            completed_at=datetime.fromisoformat(metadata["completed_at"])
            if metadata.get("completed_at")
            else None,
            estimated_hours=metadata.get("estimated_hours"),
            actual_hours=metadata.get("actual_hours"),
            tags=metadata.get("tags", []),
            project=metadata.get("project"),
            parent_id=metadata.get("parent_id"),
            dependencies=metadata.get("dependencies", []),
            recurrence=recurrence,
            recurrence_parent_id=metadata.get("recurrence_parent_id"),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            notes=notes,
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
        for path in self.base_dir.glob("*.md"):
            task = self.load_from_path(path)
            if task:
                tasks.append(task)
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
