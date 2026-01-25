"""Obsidian integration commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ...core.task_manager import TaskManager
from ...storage.obsidian import ObsidianTasksFormat, ConflictResolution

console = Console()

obsidian_app = typer.Typer(
    name="obsidian",
    help="Obsidian Tasks integration commands",
    no_args_is_help=True,
)


@obsidian_app.command(name="export")
def export_tasks(
    ctx: typer.Context,
    format: str = typer.Option(
        "tasks",
        "--format",
        "-f",
        help="Export format: 'tasks' (Obsidian Tasks format) or 'frontmatter' (YAML frontmatter)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
    include_done: bool = typer.Option(
        False, "--include-done", help="Include completed tasks"
    ),
) -> None:
    """Export tasks in Obsidian-compatible format."""
    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    formatter = ObsidianTasksFormat()

    tasks = manager.list(include_done=include_done)

    if not tasks:
        console.print("[dim]No tasks to export[/dim]")
        return

    lines = []

    if format == "tasks":
        # Export as Obsidian Tasks format
        for task in tasks:
            line = formatter.to_obsidian_line(task)
            lines.append(line)
    else:
        # Export as frontmatter format (one task per output)
        console.print("[yellow]Frontmatter export creates individual files.[/yellow]")
        console.print(f"[dim]Use --storage-dir to specify Obsidian vault location.[/dim]")
        console.print(f"\n[bold]Tasks ({len(tasks)}):[/bold]")
        for task in tasks:
            line = formatter.to_obsidian_line(task)
            console.print(f"  {line}")
        return

    output_text = "\n".join(lines)

    if output:
        output.write_text(output_text, encoding="utf-8")
        console.print(f"[green]✓[/green] Exported {len(tasks)} tasks to {output}")
    else:
        console.print(output_text)


@obsidian_app.command(name="import")
def import_tasks(
    ctx: typer.Context,
    file: Path = typer.Argument(..., help="Markdown file to import from"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be imported without making changes"
    ),
) -> None:
    """Import tasks from an Obsidian markdown file.

    Parses Obsidian Tasks format lines (- [ ] or - [x]) and creates tasks.
    """
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    formatter = ObsidianTasksFormat()

    content = file.read_text(encoding="utf-8")
    lines = content.split("\n")

    imported = []
    errors = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line.startswith("- ["):
            continue

        try:
            parsed = formatter.from_obsidian_line(line)

            if dry_run:
                status = "done" if parsed.is_completed else "pending"
                priority = parsed.priority.value if parsed.priority else "medium"
                console.print(f"  [dim]Line {i}:[/dim] {parsed.title} [{status}, {priority}]")
            else:
                from ...models.enums import Status, Priority

                task = manager.add(
                    title=parsed.title,
                    priority=parsed.priority or Priority.MEDIUM,
                    due_date=parsed.due_date,
                    scheduled_date=parsed.scheduled_date,
                    start_date=parsed.start_date,
                    tags=parsed.tags,
                )

                # Update status if completed
                if parsed.is_completed:
                    manager.complete(task.id)
                    # Update completed_at if specified
                    if parsed.completed_at:
                        task = manager.get(task.id)
                        if task:
                            task.completed_at = parsed.completed_at
                            manager.repository.update(task)

                imported.append(task)

        except ValueError as e:
            errors.append((i, line, str(e)))

    if dry_run:
        console.print(f"\n[bold]Would import {len(imported) + sum(1 for _ in [l for l in lines if l.strip().startswith('- [')])} tasks[/bold]")
        if errors:
            console.print(f"[yellow]Skipped {len(errors)} invalid lines[/yellow]")
    else:
        console.print(f"[green]✓[/green] Imported {len(imported)} tasks from {file}")
        if errors:
            console.print(f"[yellow]Warning:[/yellow] {len(errors)} lines could not be parsed")
            for line_num, line_text, error in errors[:5]:
                console.print(f"  Line {line_num}: {error}")


@obsidian_app.command(name="check")
def check_conflicts(
    ctx: typer.Context,
) -> None:
    """Check for conflicts between frontmatter and Obsidian Tasks lines.

    This command reads task files and compares the YAML frontmatter
    with any Obsidian Tasks format line in the content body.
    """
    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    formatter = ObsidianTasksFormat()

    tasks = manager.list(include_done=True)

    if not tasks:
        console.print("[dim]No tasks found[/dim]")
        return

    conflicts_found = 0

    for task in tasks:
        # Read the raw file to find Obsidian Tasks line
        task_path = manager.repository.storage._task_path(task.id)
        if not task_path.exists():
            continue

        content = task_path.read_text(encoding="utf-8")

        # Find Obsidian Tasks line in content
        obsidian_line = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("- ["):
                obsidian_line = line
                break

        if not obsidian_line:
            continue

        conflicts = formatter.detect_conflicts(task, obsidian_line)

        if conflicts:
            conflicts_found += 1
            console.print(f"\n[yellow]⚠ Conflict in task {task.short_id}:[/yellow] {task.title}")
            for conflict in conflicts:
                console.print(f"  {conflict}")

    if conflicts_found == 0:
        console.print("[green]✓[/green] No conflicts found")
    else:
        console.print(f"\n[yellow]Found {conflicts_found} task(s) with conflicts[/yellow]")
        console.print("[dim]Use 'task-butler obsidian resolve' to fix conflicts[/dim]")


@obsidian_app.command(name="resolve")
def resolve_conflicts(
    ctx: typer.Context,
    strategy: str = typer.Option(
        "frontmatter",
        "--strategy",
        "-s",
        help="Resolution strategy: 'frontmatter' (use YAML data), 'obsidian' (use Tasks line)",
    ),
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="Specific task ID to resolve (default: all)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be changed without making changes"
    ),
) -> None:
    """Resolve conflicts between frontmatter and Obsidian Tasks lines.

    When a task file contains both YAML frontmatter and an Obsidian Tasks
    line in the body, they may become inconsistent if edited in Obsidian.
    This command synchronizes them based on the chosen strategy.
    """
    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    formatter = ObsidianTasksFormat()

    if strategy not in ("frontmatter", "obsidian"):
        console.print(f"[red]Error:[/red] Invalid strategy: {strategy}")
        console.print("Use 'frontmatter' or 'obsidian'")
        raise typer.Exit(1)

    if task_id:
        task = manager.get(task_id)
        if not task:
            console.print(f"[red]Error:[/red] Task not found: {task_id}")
            raise typer.Exit(1)
        tasks = [task]
    else:
        tasks = manager.list(include_done=True)

    resolved = 0

    for task in tasks:
        task_path = manager.repository.storage._task_path(task.id)
        if not task_path.exists():
            continue

        content = task_path.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Find Obsidian Tasks line
        obsidian_line_idx = None
        obsidian_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("- ["):
                obsidian_line_idx = i
                obsidian_line = stripped
                break

        if not obsidian_line:
            continue

        conflicts = formatter.detect_conflicts(task, obsidian_line)

        if not conflicts:
            continue

        if dry_run:
            console.print(f"\n[bold]Would resolve {task.short_id}:[/bold] {task.title}")
            console.print(f"  Strategy: {strategy}")
            for conflict in conflicts:
                console.print(f"  {conflict}")
            resolved += 1
            continue

        if strategy == "frontmatter":
            # Update the Obsidian Tasks line to match frontmatter
            new_line = formatter.to_obsidian_line(task)
            lines[obsidian_line_idx] = new_line
            new_content = "\n".join(lines)
            task_path.write_text(new_content, encoding="utf-8")
        else:
            # Update frontmatter to match Obsidian Tasks line
            parsed = formatter.from_obsidian_line(obsidian_line)

            # Apply changes from parsed line
            from ...models.enums import Status, Priority

            if parsed.is_completed and task.status != Status.DONE:
                task.status = Status.DONE
                if parsed.completed_at:
                    task.completed_at = parsed.completed_at
            elif not parsed.is_completed and task.status == Status.DONE:
                task.status = Status.PENDING
                task.completed_at = None

            if parsed.priority:
                task.priority = parsed.priority

            if parsed.due_date:
                task.due_date = parsed.due_date
            if parsed.scheduled_date:
                task.scheduled_date = parsed.scheduled_date
            if parsed.start_date:
                task.start_date = parsed.start_date

            task.tags = parsed.tags

            manager.repository.update(task)

        resolved += 1
        console.print(f"[green]✓[/green] Resolved {task.short_id}: {task.title}")

    if resolved == 0:
        console.print("[dim]No conflicts to resolve[/dim]")
    else:
        action = "Would resolve" if dry_run else "Resolved"
        console.print(f"\n[green]{action} {resolved} task(s)[/green]")


@obsidian_app.command(name="format")
def format_task(
    ctx: typer.Context,
    task_id: str = typer.Argument(..., help="Task ID to format"),
) -> None:
    """Display a task in Obsidian Tasks format.

    Useful for copying the task line to paste into Obsidian notes.
    """
    storage_dir = ctx.obj.get("storage_dir") if ctx.obj else None
    manager = TaskManager(storage_dir)
    formatter = ObsidianTasksFormat()

    task = manager.get(task_id)
    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    line = formatter.to_obsidian_line(task)
    console.print(line)
