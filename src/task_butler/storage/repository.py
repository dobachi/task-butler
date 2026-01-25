"""Task repository for CRUD operations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.enums import Priority, Status
from ..models.task import Task
from .markdown import MarkdownStorage


class AmbiguousTaskIdError(Exception):
    """Raised when a short ID matches multiple tasks."""

    def __init__(self, task_id: str, matches: list[Task]):
        self.task_id = task_id
        self.matches = matches
        match_info = ", ".join(f"{t.short_id} ({t.title})" for t in matches[:5])
        if len(matches) > 5:
            match_info += f", ... (+{len(matches) - 5} more)"
        super().__init__(
            f"Ambiguous task ID '{task_id}' matches {len(matches)} tasks: {match_info}"
        )


class TaskRepository:
    """Repository for managing tasks with CRUD operations."""

    def __init__(self, storage_dir: Path | None = None, format: str = "frontmatter"):
        """Initialize repository with storage directory.

        Args:
            storage_dir: Directory to store task files
            format: Storage format - "frontmatter" (default) or "hybrid"
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".task-butler" / "tasks"
        self.storage = MarkdownStorage(storage_dir, format=format)

    def create(self, task: Task) -> Task:
        """Create a new task."""
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        self.storage.save(task)
        return task

    def find_by_prefix(self, task_id: str) -> list[Task]:
        """Find all tasks matching an ID prefix.

        Args:
            task_id: Full or partial task ID

        Returns:
            List of matching tasks
        """
        matches = []
        for t in self.storage.list_all():
            if t.id.startswith(task_id) or t.id == task_id:
                matches.append(t)
        return matches

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID (full or short ID).

        Args:
            task_id: Full UUID or short ID prefix (minimum 4 characters recommended)

        Returns:
            The matching task, or None if not found

        Raises:
            AmbiguousTaskIdError: If multiple tasks match the given ID prefix
        """
        # Try exact match first (full UUID)
        task = self.storage.load(task_id)
        if task:
            return task

        # Try to find by prefix
        matches = self.find_by_prefix(task_id)

        if len(matches) == 0:
            return None
        if len(matches) == 1:
            return matches[0]

        # Multiple matches - raise ambiguity error
        raise AmbiguousTaskIdError(task_id, matches)

    def update(self, task: Task) -> Task:
        """Update an existing task."""
        task.updated_at = datetime.now()
        self.storage.save(task)
        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task by ID."""
        task = self.get(task_id)
        if task:
            return self.storage.delete(task.id)
        return False

    def list_all(
        self,
        status: Status | None = None,
        priority: Priority | None = None,
        project: str | None = None,
        tag: str | None = None,
        parent_id: str | None = None,
        include_done: bool = False,
    ) -> list[Task]:
        """List tasks with optional filtering."""
        tasks = self.storage.list_all()

        # Filter by status
        if status:
            tasks = [t for t in tasks if t.status == status]
        elif not include_done:
            tasks = [t for t in tasks if t.status != Status.DONE]

        # Filter by priority
        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        # Filter by project
        if project:
            tasks = [t for t in tasks if t.project == project]

        # Filter by tag
        if tag:
            tasks = [t for t in tasks if tag in t.tags]

        # Filter by parent
        if parent_id is not None:
            if parent_id == "":
                # Root tasks only
                tasks = [t for t in tasks if t.parent_id is None]
            else:
                tasks = [t for t in tasks if t.parent_id == parent_id]

        return tasks

    def get_children(self, parent_id: str) -> list[Task]:
        """Get all child tasks of a parent."""
        return [t for t in self.storage.list_all() if t.parent_id == parent_id]

    def get_dependents(self, task_id: str) -> list[Task]:
        """Get tasks that depend on the given task."""
        return [t for t in self.storage.list_all() if task_id in t.dependencies]

    def get_blocking_tasks(self, task_id: str) -> list[Task]:
        """Get tasks that are blocking the given task."""
        task = self.get(task_id)
        if not task or not task.dependencies:
            return []

        blocking = []
        for dep_id in task.dependencies:
            dep_task = self.get(dep_id)
            if dep_task and dep_task.is_open:
                blocking.append(dep_task)

        return blocking

    def can_start(self, task_id: str) -> bool:
        """Check if a task can be started (no blocking dependencies)."""
        return len(self.get_blocking_tasks(task_id)) == 0

    def get_projects(self) -> list[str]:
        """Get list of all unique projects."""
        projects = set()
        for task in self.storage.list_all():
            if task.project:
                projects.add(task.project)
        return sorted(projects)

    def get_tags(self) -> list[str]:
        """Get list of all unique tags."""
        tags = set()
        for task in self.storage.list_all():
            tags.update(task.tags)
        return sorted(tags)

    def search(self, query: str) -> list[Task]:
        """Search tasks by title or description."""
        query = query.lower()
        results = []
        for task in self.storage.list_all():
            if query in task.title.lower() or query in task.description.lower():
                results.append(task)
        return results
