"""Main CLI application for Task Butler."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .commands import add, analyze, list_cmd, plan, show, status, suggest
from .commands.ai_cmd import ai_app
from .commands.config_cmd import config_app
from .commands.obsidian import obsidian_app

app = typer.Typer(
    name="task-butler",
    help="Your digital butler for task management",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
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

# AI commands
app.command(name="analyze")(analyze.analyze_tasks)
app.command(name="suggest")(suggest.suggest_tasks)
app.command(name="plan")(plan.plan_day)

# Register sub-apps
app.add_typer(ai_app, name="ai")
app.add_typer(config_app, name="config")
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
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="Save format: frontmatter (default), hybrid (includes Obsidian Tasks line)",
        envvar="TASK_BUTLER_FORMAT",
    ),
) -> None:
    """Task Butler - Your digital butler for task management."""
    ctx.ensure_object(dict)
    ctx.obj["storage_dir"] = storage_dir
    ctx.obj["format"] = format


@app.command()
def version() -> None:
    """Show version information."""
    from task_butler import __version__

    console.print(f"Task Butler v{__version__}")


@app.command()
def projects(ctx: typer.Context) -> None:
    """List all projects."""
    from ..config import get_config
    from ..core.task_manager import TaskManager

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )
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
    from ..config import get_config
    from ..core.task_manager import TaskManager

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )
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
    from ..config import get_config
    from ..core.task_manager import TaskManager
    from .commands.list_cmd import format_task_line

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )
    tasks = manager.search(query)

    if not tasks:
        console.print(f"[dim]No tasks matching '{query}'[/dim]")
        return

    console.print(f"[bold]Search results for '{query}':[/bold]")
    for task in tasks:
        console.print(format_task_line(task))


@app.command()
def organize(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Preview changes without moving files"
    ),
) -> None:
    """Organize existing tasks into Kanban directories.

    This command moves task files into status-based subdirectories
    (Backlog, InProgress, Done, Cancelled) based on their current status.

    Only works when organization.method is set to 'kanban'.
    """
    from ..config import get_config
    from ..models.enums import Status
    from ..storage.markdown import MarkdownStorage

    config = get_config()
    organization = config.get_organization_method()

    if organization != "kanban":
        console.print("[yellow]Warning:[/yellow] Organization method is 'flat', not 'kanban'.")
        console.print("To enable Kanban mode, run:")
        console.print("  task-butler config set organization.method kanban")
        raise typer.Exit(1)

    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format_type = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    kanban_dirs = config.get_kanban_dirs()

    # First, load all tasks from flat structure (base_dir only)
    flat_storage = MarkdownStorage(storage_dir, format=format_type, organization="flat")
    tasks = flat_storage.list_all()

    if not tasks:
        console.print("[dim]No tasks to organize[/dim]")
        return

    # Create kanban storage for target directories
    kanban_storage = MarkdownStorage(
        storage_dir,
        format=format_type,
        organization="kanban",
        kanban_dirs=kanban_dirs,
    )

    # Status to directory name mapping
    status_to_dir = {
        Status.PENDING: kanban_dirs.get("backlog", "Backlog"),
        Status.IN_PROGRESS: kanban_dirs.get("in_progress", "InProgress"),
        Status.DONE: kanban_dirs.get("done", "Done"),
        Status.CANCELLED: kanban_dirs.get("cancelled", "Cancelled"),
    }

    moved_count = 0
    for task in tasks:
        target_dir = status_to_dir.get(task.status, kanban_dirs.get("backlog", "Backlog"))
        current_path = flat_storage._find_task_file(task.id)

        # Skip if already in correct directory
        if current_path.parent.name == target_dir:
            continue

        # Only count tasks in base_dir (not already organized)
        if current_path.parent != storage_dir:
            continue

        if dry_run:
            console.print(f"[dim]Would move:[/dim] {current_path.name} → {target_dir}/")
        else:
            # Use kanban_storage to save (will move to correct dir)
            kanban_storage.save(task)
            console.print(f"[green]✓[/green] Moved: {task.short_id} ({task.title}) → {target_dir}/")

        moved_count += 1

    if moved_count == 0:
        console.print("[dim]All tasks are already organized[/dim]")
    elif dry_run:
        console.print(
            f"\n[bold]{moved_count}[/bold] task(s) would be moved. Run without --dry-run to apply."
        )
    else:
        console.print(f"\n[bold]{moved_count}[/bold] task(s) organized.")


if __name__ == "__main__":
    app()
