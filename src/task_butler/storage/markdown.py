"""Markdown file storage for tasks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import frontmatter

from ..models.task import Task, Note, RecurrenceRule
from ..models.enums import Status, Priority, Frequency


class MarkdownStorage:
    """Read and write tasks as Markdown files with YAML frontmatter."""

    def __init__(self, base_dir: Path):
        """Initialize storage with base directory."""
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _task_path(self, task_id: str) -> Path:
        """Get file path for a task."""
        return self.base_dir / f"{task_id}.md"

    def save(self, task: Task) -> Path:
        """Save a task to a Markdown file."""
        path = self._task_path(task.id)

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
        path = self._task_path(task_id)
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
        path = self._task_path(task_id)
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
        return self._task_path(task_id).exists()
