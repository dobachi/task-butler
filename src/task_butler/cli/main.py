"""Main CLI application for Task Butler."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .commands import add, list_cmd, show, status
from .commands.obsidian import obsidian_app

app = typer.Typer(
    name="task-butler",
    help="Your digital butler for task management",
    no_args_is_help=True,
)

console = Console()

# Register commands
app.command(name="add")(add.add_task)
app.command(name="list")(list_cmd.list_tasks)
app.command(name="ls")(list_cmd.list_tasks)  # Alias
app.command(name="show")(show.show_task)
app.command(name="start")(status.start_task)
app.command(name="done")(status.done_task)
app.command(name="cancel")(status.cancel_task)
app.command(name="delete")(status.delete_task)
app.command(name="note")(status.add_note)

# Register sub-apps
app.add_typer(obsidian_app, name="obsidian")


@app.callback()
def main(
    ctx: typer.Context,
    storage_dir: Optional[Path] = typer.Option(
        None,
        "--storage-dir",
        "-d",
        help="Directory for task storage (default: ~/.task-butler/tasks)",
        envvar="TASK_BUTLER_DIR",
    ),
) -> None:
    """Task Butler - Your digital butler for task management."""
    ctx.ensure_object(dict)
    ctx.obj["storage_dir"] = storage_dir


@app.command()
def version() -> None:
    """Show version information."""
    from task_butler import __version__

    console.print(f"Task Butler v{__version__}")


@app.command()
def projects(ctx: typer.Context) -> None:
    """List all projects."""
    from ..core.task_manager import TaskManager

    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    project_list = manager.get_projects()

    if not project_list:
        console.print("[dim]No projects found[/dim]")
        return

    console.print("[bold]Projects:[/bold]")
    for project in project_list:
        console.print(f"  - {project}")


@app.command()
def tags(ctx: typer.Context) -> None:
    """List all tags."""
    from ..core.task_manager import TaskManager

    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    tag_list = manager.get_tags()

    if not tag_list:
        console.print("[dim]No tags found[/dim]")
        return

    console.print("[bold]Tags:[/bold]")
    for tag in tag_list:
        console.print(f"  - {tag}")


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
) -> None:
    """Search tasks by title or description."""
    from ..core.task_manager import TaskManager
    from .commands.list_cmd import format_task_line

    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    tasks = manager.search(query)

    if not tasks:
        console.print(f"[dim]No tasks matching '{query}'[/dim]")
        return

    console.print(f"[bold]Search results for '{query}':[/bold]")
    for task in tasks:
        console.print(format_task_line(task))


if __name__ == "__main__":
    app()
