"""Task manager - main interface for task operations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..models.task import Task, RecurrenceRule
from ..models.enums import Status, Priority, Frequency
from ..storage.repository import TaskRepository
from .recurrence import RecurrenceGenerator


class TaskManager:
    """Main interface for managing tasks."""

    def __init__(self, storage_dir: Path | None = None):
        """Initialize task manager."""
        self.repository = TaskRepository(storage_dir)
        self.recurrence = RecurrenceGenerator()

    def add(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        due_date: datetime | None = None,
        tags: list[str] | None = None,
        project: str | None = None,
        parent_id: str | None = None,
        dependencies: list[str] | None = None,
        estimated_hours: float | None = None,
        recurrence: RecurrenceRule | None = None,
    ) -> Task:
        """Add a new task."""
        # Validate parent exists if specified
        if parent_id:
            parent = self.repository.get(parent_id)
            if not parent:
                raise ValueError(f"Parent task not found: {parent_id}")
            parent_id = parent.id  # Use full ID

        # Validate dependencies exist
        dep_ids = []
        if dependencies:
            for dep_id in dependencies:
                dep = self.repository.get(dep_id)
                if not dep:
                    raise ValueError(f"Dependency task not found: {dep_id}")
                dep_ids.append(dep.id)

        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            tags=tags or [],
            project=project,
            parent_id=parent_id,
            dependencies=dep_ids,
            estimated_hours=estimated_hours,
            recurrence=recurrence,
        )

        return self.repository.create(task)

    def get(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self.repository.get(task_id)

    def list(
        self,
        status: Status | None = None,
        priority: Priority | None = None,
        project: str | None = None,
        tag: str | None = None,
        parent_id: str | None = None,
        include_done: bool = False,
    ) -> list[Task]:
        """List tasks with optional filters."""
        tasks = self.repository.list_all(
            status=status,
            priority=priority,
            project=project,
            tag=tag,
            parent_id=parent_id,
            include_done=include_done,
        )

        # Sort by priority (urgent first) then by due date
        priority_order = {
            Priority.URGENT: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }

        def sort_key(t: Task) -> tuple:
            pri = priority_order.get(t.priority, 99)
            due = t.due_date or datetime.max
            return (pri, due, t.created_at)

        return sorted(tasks, key=sort_key)

    def start(self, task_id: str) -> Task:
        """Start working on a task."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Check if task can be started (no blocking dependencies)
        blocking = self.repository.get_blocking_tasks(task.id)
        if blocking:
            titles = [t.title for t in blocking]
            raise ValueError(f"Task is blocked by: {', '.join(titles)}")

        task.start()
        return self.repository.update(task)

    def complete(self, task_id: str, actual_hours: float | None = None) -> Task:
        """Mark a task as done."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.complete(actual_hours)
        updated_task = self.repository.update(task)

        # If this is a recurring task instance, create the next one
        if task.recurrence_parent_id:
            parent = self.repository.get(task.recurrence_parent_id)
            if parent and parent.recurrence:
                instances = self._get_recurrence_instances(parent.id)
                if self.recurrence.should_generate_next(parent, instances):
                    next_instance = self.recurrence.create_next_instance(parent)
                    if next_instance:
                        self.repository.create(next_instance)

        return updated_task

    def cancel(self, task_id: str) -> Task:
        """Cancel a task."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.cancel()
        return self.repository.update(task)

    def delete(self, task_id: str) -> bool:
        """Delete a task."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        # Check for dependent tasks
        dependents = self.repository.get_dependents(task.id)
        if dependents:
            titles = [t.title for t in dependents]
            raise ValueError(f"Cannot delete: other tasks depend on this: {', '.join(titles)}")

        # Check for child tasks
        children = self.repository.get_children(task.id)
        if children:
            raise ValueError(f"Cannot delete: task has {len(children)} child task(s)")

        return self.repository.delete(task.id)

    def add_note(self, task_id: str, content: str) -> Task:
        """Add a note to a task."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        task.add_note(content)
        return self.repository.update(task)

    def update(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: datetime | None = None,
        tags: list[str] | None = None,
        project: str | None = None,
        estimated_hours: float | None = None,
    ) -> Task:
        """Update task fields."""
        task = self.repository.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if due_date is not None:
            task.due_date = due_date
        if tags is not None:
            task.tags = tags
        if project is not None:
            task.project = project
        if estimated_hours is not None:
            task.estimated_hours = estimated_hours

        return self.repository.update(task)

    def search(self, query: str) -> list[Task]:
        """Search tasks by title or description."""
        return self.repository.search(query)

    def get_projects(self) -> list[str]:
        """Get list of all projects."""
        return self.repository.get_projects()

    def get_tags(self) -> list[str]:
        """Get list of all tags."""
        return self.repository.get_tags()

    def get_tree(self, root_id: str | None = None) -> list[tuple[Task, int]]:
        """Get tasks as a tree structure with depth levels."""
        result: list[tuple[Task, int]] = []

        def add_children(parent_id: str | None, depth: int) -> None:
            children = self.repository.list_all(parent_id=parent_id or "")
            if parent_id:
                children = self.repository.get_children(parent_id)

            for child in sorted(children, key=lambda t: t.created_at):
                result.append((child, depth))
                add_children(child.id, depth + 1)

        add_children(root_id, 0)
        return result

    def _get_recurrence_instances(self, parent_id: str) -> list[Task]:
        """Get all instances of a recurring task."""
        return [
            t
            for t in self.repository.list_all(include_done=True)
            if t.recurrence_parent_id == parent_id
        ]

    def generate_recurring_tasks(self) -> list[Task]:
        """Generate next instances for all recurring tasks that need them."""
        generated = []

        for task in self.repository.list_all(include_done=True):
            if not task.is_recurring:
                continue

            instances = self._get_recurrence_instances(task.id)
            if self.recurrence.should_generate_next(task, instances):
                next_instance = self.recurrence.create_next_instance(task)
                if next_instance:
                    created = self.repository.create(next_instance)
                    generated.append(created)

        return generated
