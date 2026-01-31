"""List tasks command."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ...core.task_manager import TaskManager
from ...models.enums import Priority, Status
from ...models.task import Task

console = Console()


def format_task_line(task: Task) -> str:
    """Format a single task line for display."""
    # Status indicator
    status_icons = {
        Status.PENDING: "[yellow]○[/yellow]",
        Status.IN_PROGRESS: "[blue]◐[/blue]",
        Status.DONE: "[green]●[/green]",
        Status.CANCELLED: "[dim]✗[/dim]",
    }

    # Priority indicator
    priority_colors = {
        Priority.URGENT: "[red bold]!![/red bold]",
        Priority.HIGH: "[red]![/red]",
        Priority.MEDIUM: "[yellow]·[/yellow]",
        Priority.LOW: "[dim]·[/dim]",
    }

    parts = [
        status_icons.get(task.status, "○"),
        priority_colors.get(task.priority, "·"),
        f"[cyan]{task.short_id}[/cyan]",
        task.title,
    ]

    # Add due date if present
    if task.due_date:
        from datetime import datetime

        today = datetime.now().date()
        due_date = task.due_date.date()

        if due_date < today:
            parts.append(f"[red]({task.due_date.strftime('%m/%d')} overdue)[/red]")
        elif due_date == today:
            parts.append("[yellow](today)[/yellow]")
        else:
            parts.append(f"[dim]({task.due_date.strftime('%m/%d')})[/dim]")

    # Add project
    if task.project:
        parts.append(f"[magenta]@{task.project}[/magenta]")

    # Add tags
    if task.tags:
        tag_str = " ".join(f"[blue]#{t}[/blue]" for t in task.tags)
        parts.append(tag_str)

    return " ".join(parts)


def list_tasks(
    ctx: typer.Context,
    all: bool = typer.Option(False, "--all", "-a", help="Include completed tasks"),
    status: Optional[Status] = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: Optional[Priority] = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    project: Optional[str] = typer.Option(None, "--project", "-P", help="Filter by project"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    tree: bool = typer.Option(False, "--tree", help="Show as tree structure"),
    table: bool = typer.Option(False, "--table", help="Show as table"),
) -> None:
    """List tasks."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )

    if tree:
        _list_tree(manager, all)
    elif table:
        _list_table(manager, status, priority, project, tag, all)
    else:
        _list_simple(manager, status, priority, project, tag, all)


def _list_simple(
    manager: TaskManager,
    status: Optional[Status],
    priority: Optional[Priority],
    project: Optional[str],
    tag: Optional[str],
    include_done: bool,
) -> None:
    """Simple list format."""
    tasks = manager.list(
        status=status,
        priority=priority,
        project=project,
        tag=tag,
        include_done=include_done,
    )

    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    for task in tasks:
        console.print(format_task_line(task))

    console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")


def _list_table(
    manager: TaskManager,
    status: Optional[Status],
    priority: Optional[Priority],
    project: Optional[str],
    tag: Optional[str],
    include_done: bool,
) -> None:
    """Table format."""
    tasks = manager.list(
        status=status,
        priority=priority,
        project=project,
        tag=tag,
        include_done=include_done,
    )

    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Status", width=10)
    table.add_column("Pri", width=4)
    table.add_column("Title")
    table.add_column("Due", width=10)
    table.add_column("Project", style="magenta")

    status_display = {
        Status.PENDING: "[yellow]pending[/yellow]",
        Status.IN_PROGRESS: "[blue]working[/blue]",
        Status.DONE: "[green]done[/green]",
        Status.CANCELLED: "[dim]cancelled[/dim]",
    }

    priority_display = {
        Priority.URGENT: "[red bold]URGENT[/red bold]",
        Priority.HIGH: "[red]high[/red]",
        Priority.MEDIUM: "[yellow]medium[/yellow]",
        Priority.LOW: "[dim]low[/dim]",
    }

    for task in tasks:
        due_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else "-"
        table.add_row(
            task.short_id,
            status_display.get(task.status, str(task.status.value)),
            priority_display.get(task.priority, str(task.priority.value)),
            task.title,
            due_str,
            task.project or "-",
        )

    console.print(table)


def _list_tree(manager: TaskManager, include_done: bool) -> None:
    """Tree format showing hierarchy."""
    tree_data = manager.get_tree()

    if not tree_data:
        console.print("[dim]No tasks found[/dim]")
        return

    for task, depth in tree_data:
        if not include_done and task.status == Status.DONE:
            continue

        indent = "  " * depth
        line = format_task_line(task)
        console.print(f"{indent}{line}")
