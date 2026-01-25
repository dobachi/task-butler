"""Task status commands (start, done, cancel, delete, note)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

from ...core.task_manager import TaskManager

console = Console()


def start_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
) -> None:
    """Start working on a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        task = manager.start(task_id)
        console.print(f"[blue]◐[/blue] Started: [bold]{task.title}[/bold]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def done_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
    hours: Optional[float] = typer.Option(None, "--hours", "-h", help="Actual hours spent"),
) -> None:
    """Mark a task as done."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        task = manager.complete(task_id, hours)
        console.print(f"[green]●[/green] Completed: [bold]{task.title}[/bold]")

        if hours:
            console.print(f"  Logged: {hours}h")

        # Check if this was a recurring task
        if task.recurrence_parent_id:
            console.print("[dim]  Next instance will be generated automatically[/dim]")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def cancel_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
) -> None:
    """Cancel a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        task = manager.cancel(task_id)
        console.print(f"[dim]✗[/dim] Cancelled: [bold]{task.title}[/bold]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def delete_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task permanently."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    task = manager.get(task_id)
    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete '{task.title}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        manager.delete(task_id)
        console.print(f"[red]Deleted:[/red] {task.title}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def add_note(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
    content: str = typer.Argument(..., help="Note content"),
) -> None:
    """Add a note to a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        task = manager.add_note(task_id, content)
        console.print(f"[green]✓[/green] Note added to: [bold]{task.title}[/bold]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
