"""Task status commands (start, done, cancel, delete, note)."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from ...core.task_manager import TaskManager
from ...storage import AmbiguousTaskIdError
from ..completion import complete_open_task_id, complete_task_id

console = Console()


def _handle_ambiguous_id(e: AmbiguousTaskIdError) -> None:
    """Display ambiguous task ID error."""
    console.print(f"[red]Error:[/red] Ambiguous task ID '{e.task_id}'")
    console.print("Matching tasks:")
    for t in e.matches:
        console.print(f"  {t.short_id} - {t.title}")


def start_task(
    ctx: typer.Context,
    task_id: Annotated[
        str,
        typer.Argument(..., help="Task ID (full or short)", autocompletion=complete_open_task_id),
    ],
) -> None:
    """Start working on a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs)

    try:
        task = manager.start(task_id)
        console.print(f"[blue]◐[/blue] Started: [bold]{task.title}[/bold]")
    except AmbiguousTaskIdError as e:
        _handle_ambiguous_id(e)
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def done_task(
    ctx: typer.Context,
    task_id: Annotated[
        str,
        typer.Argument(..., help="Task ID (full or short)", autocompletion=complete_open_task_id),
    ],
    hours: Optional[float] = typer.Option(None, "--hours", "-h", help="Actual hours spent"),
) -> None:
    """Mark a task as done."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs)

    try:
        task = manager.complete(task_id, hours)
        console.print(f"[green]●[/green] Completed: [bold]{task.title}[/bold]")

        if hours:
            console.print(f"  Logged: {hours}h")

        # Check if this was a recurring task
        if task.recurrence_parent_id:
            console.print("[dim]  Next instance will be generated automatically[/dim]")

    except AmbiguousTaskIdError as e:
        _handle_ambiguous_id(e)
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def cancel_task(
    ctx: typer.Context,
    task_id: Annotated[
        str,
        typer.Argument(..., help="Task ID (full or short)", autocompletion=complete_open_task_id),
    ],
) -> None:
    """Cancel a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs)

    try:
        task = manager.cancel(task_id)
        console.print(f"[dim]✗[/dim] Cancelled: [bold]{task.title}[/bold]")
    except AmbiguousTaskIdError as e:
        _handle_ambiguous_id(e)
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def delete_task(
    ctx: typer.Context,
    task_id: Annotated[
        str,
        typer.Argument(..., help="Task ID (full or short)", autocompletion=complete_task_id),
    ],
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a task permanently."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs)

    try:
        task = manager.get(task_id)
    except AmbiguousTaskIdError as e:
        _handle_ambiguous_id(e)
        raise typer.Exit(1)

    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    if not force:
        confirm = typer.confirm(f"Delete '{task.title}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(0)

    try:
        manager.delete(task.id)  # Use full ID to avoid re-lookup
        console.print(f"[red]Deleted:[/red] {task.title}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def add_note(
    ctx: typer.Context,
    task_id: Annotated[
        str,
        typer.Argument(..., help="Task ID (full or short)", autocompletion=complete_task_id),
    ],
    content: str = typer.Argument(..., help="Note content"),
) -> None:
    """Add a note to a task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs)

    try:
        task = manager.add_note(task_id, content)
        console.print(f"[green]✓[/green] Note added to: [bold]{task.title}[/bold]")
    except AmbiguousTaskIdError as e:
        _handle_ambiguous_id(e)
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
