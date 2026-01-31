"""Shell completion functions for CLI arguments."""

from __future__ import annotations


def _get_manager():
    """Get TaskManager instance with current config."""
    from ..config import get_config
    from ..core.task_manager import TaskManager

    config = get_config()
    storage_dir = config.get_storage_dir()
    format = config.get_format()
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    return TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )


def complete_task_id(incomplete: str) -> list[tuple[str, str]]:
    """Complete any task ID.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of (task_id, help_text) tuples for matching tasks
    """
    try:
        manager = _get_manager()
        tasks = manager.list(include_done=True)
        results: list[tuple[str, str]] = []

        incomplete_lower = incomplete.lower()
        for task in tasks:
            short_id = task.short_id
            # Match if short_id starts with incomplete string
            if short_id.lower().startswith(incomplete_lower):
                results.append((short_id, task.title))

        return results
    except Exception:
        # Completion should never fail - return empty on error
        return []


def complete_open_task_id(incomplete: str) -> list[tuple[str, str]]:
    """Complete only open (pending/in_progress) task IDs.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of (task_id, help_text) tuples for matching open tasks
    """
    from ..models.enums import Status

    try:
        manager = _get_manager()
        tasks = manager.list(include_done=False)  # Only open tasks
        results: list[tuple[str, str]] = []

        incomplete_lower = incomplete.lower()
        for task in tasks:
            if task.status in (Status.PENDING, Status.IN_PROGRESS):
                short_id = task.short_id
                if short_id.lower().startswith(incomplete_lower):
                    # Add status indicator to help text
                    status_icon = "◐" if task.status == Status.IN_PROGRESS else "○"
                    results.append((short_id, f"{status_icon} {task.title}"))

        return results
    except Exception:
        return []


def complete_project_name(incomplete: str) -> list[str]:
    """Complete project names.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching project names
    """
    try:
        manager = _get_manager()
        projects = manager.get_projects()

        incomplete_lower = incomplete.lower()
        return [p for p in projects if p.lower().startswith(incomplete_lower)]
    except Exception:
        return []


def complete_tag_name(incomplete: str) -> list[str]:
    """Complete tag names.

    Args:
        incomplete: The partial input to complete

    Returns:
        List of matching tag names
    """
    try:
        manager = _get_manager()
        tags = manager.get_tags()

        incomplete_lower = incomplete.lower()
        return [t for t in tags if t.lower().startswith(incomplete_lower)]
    except Exception:
        return []
