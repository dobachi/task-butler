"""Show task details command."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from ...core.task_manager import TaskManager
from ...models.enums import Priority, Status
from ...storage import AmbiguousTaskIdError

console = Console()


def show_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
) -> None:
    """Show detailed information about a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        task = manager.get(task_id)
    except AmbiguousTaskIdError as e:
        console.print(f"[red]Error:[/red] Ambiguous task ID '{task_id}'")
        console.print("Matching tasks:")
        for t in e.matches:
            console.print(f"  {t.short_id} - {t.title}")
        raise typer.Exit(1)

    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    # Status and priority colors
    status_colors = {
        Status.PENDING: "yellow",
        Status.IN_PROGRESS: "blue",
        Status.DONE: "green",
        Status.CANCELLED: "dim",
    }

    priority_colors = {
        Priority.URGENT: "red bold",
        Priority.HIGH: "red",
        Priority.MEDIUM: "yellow",
        Priority.LOW: "dim",
    }

    # Build content
    lines = []

    # Status and priority
    status_color = status_colors.get(task.status, "white")
    priority_color = priority_colors.get(task.priority, "white")
    lines.append(
        f"[{status_color}]{task.status.value}[/{status_color}] | "
        f"[{priority_color}]{task.priority.value}[/{priority_color}]"
    )
    lines.append("")

    # Description
    if task.description:
        lines.append("[bold]Description:[/bold]")
        lines.append(task.description)
        lines.append("")

    # Time info
    if task.due_date or task.estimated_hours or task.actual_hours:
        lines.append("[bold]Time:[/bold]")
        if task.due_date:
            lines.append(f"  Due: {task.due_date.strftime('%Y-%m-%d')}")
        if task.estimated_hours:
            lines.append(f"  Estimated: {task.estimated_hours}h")
        if task.actual_hours:
            lines.append(f"  Actual: {task.actual_hours}h")
        lines.append("")

    # Classification
    if task.project or task.tags:
        lines.append("[bold]Classification:[/bold]")
        if task.project:
            lines.append(f"  Project: [magenta]{task.project}[/magenta]")
        if task.tags:
            tag_str = ", ".join(f"[blue]#{t}[/blue]" for t in task.tags)
            lines.append(f"  Tags: {tag_str}")
        lines.append("")

    # Dependencies
    if task.dependencies:
        lines.append("[bold]Dependencies:[/bold]")
        blocking = manager.repository.get_blocking_tasks(task.id)
        blocking_ids = {t.id for t in blocking}

        for dep_id in task.dependencies:
            dep_task = manager.get(dep_id)
            if dep_task:
                if dep_task.id in blocking_ids:
                    lines.append(f"  [red]✗[/red] {dep_task.short_id} - {dep_task.title}")
                else:
                    lines.append(f"  [green]✓[/green] {dep_task.short_id} - {dep_task.title}")
            else:
                lines.append(f"  [dim]?[/dim] {dep_id[:8]} - (not found)")
        lines.append("")

    # Parent/children
    if task.parent_id:
        parent = manager.get(task.parent_id)
        if parent:
            lines.append(f"[bold]Parent:[/bold] {parent.short_id} - {parent.title}")
            lines.append("")

    children = manager.repository.get_children(task.id)
    if children:
        lines.append("[bold]Subtasks:[/bold]")
        for child in children:
            status_icon = {
                Status.PENDING: "[yellow]○[/yellow]",
                Status.IN_PROGRESS: "[blue]◐[/blue]",
                Status.DONE: "[green]●[/green]",
                Status.CANCELLED: "[dim]✗[/dim]",
            }.get(child.status, "○")
            lines.append(f"  {status_icon} {child.short_id} - {child.title}")
        lines.append("")

    # Recurrence
    if task.recurrence:
        lines.append("[bold]Recurrence:[/bold]")
        freq = task.recurrence.frequency.value
        if task.recurrence.interval > 1:
            lines.append(f"  Every {task.recurrence.interval} {freq}")
        else:
            lines.append(f"  {freq.capitalize()}")
        if task.recurrence.end_date:
            lines.append(f"  Until: {task.recurrence.end_date.strftime('%Y-%m-%d')}")
        lines.append("")

    if task.recurrence_parent_id:
        parent = manager.get(task.recurrence_parent_id)
        if parent:
            lines.append(f"[bold]Recurring from:[/bold] {parent.short_id} - {parent.title}")
            lines.append("")

    # Notes
    if task.notes:
        lines.append("[bold]Notes:[/bold]")
        for note in task.notes:
            timestamp = note.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"  [{timestamp}] {note.content}")
        lines.append("")

    # Metadata
    lines.append("[dim]─" * 40 + "[/dim]")
    lines.append(f"[dim]ID: {task.id}[/dim]")
    lines.append(f"[dim]Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")
    lines.append(f"[dim]Updated: {task.updated_at.strftime('%Y-%m-%d %H:%M')}[/dim]")

    # Display
    content = "\n".join(lines)
    panel = Panel(
        content,
        title=f"[bold]{task.title}[/bold]",
        subtitle=f"[cyan]{task.short_id}[/cyan]",
        border_style=status_color,
    )
    console.print(panel)
