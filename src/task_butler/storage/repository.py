"""Task repository for CRUD operations."""

from pathlib import Path
from datetime import datetime

from ..models.task import Task
from ..models.enums import Status, Priority
from .markdown import MarkdownStorage


class TaskRepository:
    """Repository for managing tasks with CRUD operations."""

    def __init__(self, storage_dir: Path | None = None):
        """Initialize repository with storage directory."""
        if storage_dir is None:
            storage_dir = Path.home() / ".task-butler" / "tasks"
        self.storage = MarkdownStorage(storage_dir)

    def create(self, task: Task) -> Task:
        """Create a new task."""
        task.created_at = datetime.now()
        task.updated_at = datetime.now()
        self.storage.save(task)
        return task

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID (full or short ID)."""
        # Try full ID first
        task = self.storage.load(task_id)
        if task:
            return task

        # Try to find by short ID
        for t in self.storage.list_all():
            if t.id.startswith(task_id):
                return t

        return None

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
