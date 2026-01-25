"""Obsidian integration commands."""

from __future__ import annotations

import fnmatch
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from ...core.task_manager import TaskManager
from ...models.enums import Status, Priority
from ...models.task import Task
from ...storage.obsidian import ObsidianTasksFormat, ConflictResolution, ParsedObsidianTask

console = Console()


class DuplicateAction(str, Enum):
    """Action to take when a duplicate is found."""

    SKIP = "skip"
    UPDATE = "update"
    FORCE = "force"
    INTERACTIVE = "interactive"

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
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=storage_format)
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


def _collect_files(path: Path, recursive: bool, pattern: str) -> list[Path]:
    """Collect markdown files from a path.

    Args:
        path: File or directory path
        recursive: Include subdirectories
        pattern: Glob pattern for file matching

    Returns:
        List of file paths to process
    """
    if path.is_file():
        return [path]

    if recursive:
        files = list(path.rglob(pattern))
    else:
        files = list(path.glob(pattern))

    return sorted([f for f in files if f.is_file()])


def _prompt_duplicate_action(
    existing_task: Task, parsed: ParsedObsidianTask
) -> str:
    """Prompt user for action on duplicate task.

    Args:
        existing_task: The existing task in storage
        parsed: The parsed task from Obsidian

    Returns:
        User's choice: 's' (skip), 'u' (update), 'f' (force), 'a' (all skip), 'A' (all update)
    """
    console.print(f"\n[yellow]⚠ Duplicate found:[/yellow] \"{parsed.title}\"")
    if parsed.due_date:
        console.print(f"  Due: {parsed.due_date.strftime('%Y-%m-%d')}")
    console.print(f"  Existing task: [cyan]{existing_task.short_id}[/cyan]")

    while True:
        choice = console.input(
            "[dim][s]kip, [u]pdate, [f]orce create, [a]ll skip, [A]ll update:[/dim] "
        )
        if choice in ("s", "u", "f", "a", "A"):
            return choice
        console.print("[red]Invalid choice. Use s/u/f/a/A[/red]")


def _import_single_file(
    file: Path,
    manager: TaskManager,
    formatter: ObsidianTasksFormat,
    duplicate_action: DuplicateAction,
    dry_run: bool,
    global_action: dict,
) -> tuple[list, list, list, list]:
    """Import tasks from a single file.

    Args:
        file: File path to import
        manager: TaskManager instance
        formatter: ObsidianTasksFormat instance
        duplicate_action: How to handle duplicates
        dry_run: Preview only
        global_action: Mutable dict for storing user's "all" choice

    Returns:
        Tuple of (imported, updated, skipped, errors) lists
    """
    content = file.read_text(encoding="utf-8")
    lines = content.split("\n")

    imported = []
    updated = []
    skipped = []
    errors = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line.startswith("- ["):
            continue

        try:
            parsed = formatter.from_obsidian_line(line)

            # Check for duplicates
            existing = manager.find_duplicate(parsed.title, parsed.due_date)

            if existing:
                # Determine action
                action = global_action.get("action", duplicate_action)

                if action == DuplicateAction.INTERACTIVE:
                    choice = _prompt_duplicate_action(existing, parsed)
                    if choice == "a":
                        global_action["action"] = DuplicateAction.SKIP
                        action = DuplicateAction.SKIP
                    elif choice == "A":
                        global_action["action"] = DuplicateAction.UPDATE
                        action = DuplicateAction.UPDATE
                    elif choice == "s":
                        action = DuplicateAction.SKIP
                    elif choice == "u":
                        action = DuplicateAction.UPDATE
                    elif choice == "f":
                        action = DuplicateAction.FORCE

                if action == DuplicateAction.SKIP:
                    if dry_run:
                        console.print(
                            f"  [dim]Line {i}:[/dim] [yellow]SKIP[/yellow] {parsed.title} "
                            f"(duplicate of {existing.short_id})"
                        )
                    skipped.append((parsed, existing))
                    continue

                elif action == DuplicateAction.UPDATE:
                    if dry_run:
                        console.print(
                            f"  [dim]Line {i}:[/dim] [blue]UPDATE[/blue] {parsed.title} "
                            f"(existing: {existing.short_id})"
                        )
                    else:
                        # Update existing task
                        manager.update(
                            existing.id,
                            priority=parsed.priority or existing.priority,
                            due_date=parsed.due_date,
                            scheduled_date=parsed.scheduled_date,
                            start_date=parsed.start_date,
                            tags=parsed.tags if parsed.tags else None,
                        )

                        # Handle status change
                        if parsed.is_completed and existing.status != Status.DONE:
                            manager.complete(existing.id)
                            if parsed.completed_at:
                                task = manager.get(existing.id)
                                if task:
                                    task.completed_at = parsed.completed_at
                                    manager.repository.update(task)

                        updated.append(existing)
                    continue

                # FORCE: fall through to create new task

            # Create new task
            if dry_run:
                status = "done" if parsed.is_completed else "pending"
                priority = parsed.priority.value if parsed.priority else "medium"
                console.print(
                    f"  [dim]Line {i}:[/dim] [green]NEW[/green] {parsed.title} [{status}, {priority}]"
                )
                imported.append(parsed)
            else:
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
                    if parsed.completed_at:
                        task = manager.get(task.id)
                        if task:
                            task.completed_at = parsed.completed_at
                            manager.repository.update(task)

                imported.append(task)

        except ValueError as e:
            errors.append((i, line, str(e)))

    return imported, updated, skipped, errors


@obsidian_app.command(name="import")
def import_tasks(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="File or directory to import from"),
    recursive: bool = typer.Option(
        False, "--recursive", "-r", help="Include subdirectories"
    ),
    pattern: str = typer.Option(
        "*.md", "--pattern", "-p", help="File pattern for directory import"
    ),
    skip: bool = typer.Option(
        False, "--skip", help="Skip duplicate tasks (default behavior)"
    ),
    update: bool = typer.Option(
        False, "--update", help="Update existing tasks on duplicate"
    ),
    force: bool = typer.Option(
        False, "--force", help="Force create even if duplicate exists"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Prompt for each duplicate"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be imported without making changes"
    ),
) -> None:
    """Import tasks from Obsidian markdown file(s).

    Parses Obsidian Tasks format lines (- [ ] or - [x]) and creates tasks.

    Examples:
        # Import single file
        task-butler obsidian import ~/Vault/daily/2025-01-25.md

        # Import all files in directory
        task-butler obsidian import ~/Vault/daily/

        # Import recursively
        task-butler obsidian import ~/Vault/ --recursive

        # Preview without changes
        task-butler obsidian import ~/Vault/daily/ --dry-run

        # Update existing tasks on duplicate
        task-butler obsidian import ~/Vault/daily/ --update

        # Interactive mode
        task-butler obsidian import ~/Vault/daily/ --interactive
    """
    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    # Determine duplicate action (mutually exclusive options)
    action_count = sum([skip, update, force, interactive])
    if action_count > 1:
        console.print("[red]Error:[/red] Options --skip, --update, --force, --interactive are mutually exclusive")
        raise typer.Exit(1)

    if update:
        duplicate_action = DuplicateAction.UPDATE
    elif force:
        duplicate_action = DuplicateAction.FORCE
    elif interactive:
        duplicate_action = DuplicateAction.INTERACTIVE
    else:
        duplicate_action = DuplicateAction.SKIP  # Default

    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=storage_format)
    formatter = ObsidianTasksFormat()

    # Collect files to process
    files = _collect_files(path, recursive, pattern)

    if not files:
        console.print(f"[yellow]No files found matching pattern '{pattern}' in {path}[/yellow]")
        return

    if path.is_dir():
        console.print(f"[bold]Processing {len(files)} file(s) from {path}[/bold]")
        if recursive:
            console.print(f"[dim](recursive mode)[/dim]")

    total_imported = []
    total_updated = []
    total_skipped = []
    total_errors = []
    global_action: dict = {}  # For storing "all skip" or "all update" choice

    for file in files:
        if len(files) > 1:
            console.print(f"\n[cyan]{file.name}:[/cyan]")

        imported, updated, skipped, errors = _import_single_file(
            file, manager, formatter, duplicate_action, dry_run, global_action
        )

        total_imported.extend(imported)
        total_updated.extend(updated)
        total_skipped.extend(skipped)
        total_errors.extend(errors)

    # Summary
    console.print()
    if dry_run:
        console.print("[bold]Dry run summary:[/bold]")
        console.print(f"  Would import: {len(total_imported)} new task(s)")
        if total_updated:
            console.print(f"  Would update: {len(total_updated)} existing task(s)")
        if total_skipped:
            console.print(f"  Would skip: {len(total_skipped)} duplicate(s)")
        if total_errors:
            console.print(f"  [yellow]Parse errors: {len(total_errors)}[/yellow]")
    else:
        console.print(f"[green]✓[/green] Imported {len(total_imported)} new task(s)")
        if total_updated:
            console.print(f"[blue]✓[/blue] Updated {len(total_updated)} existing task(s)")
        if total_skipped:
            console.print(f"[dim]Skipped {len(total_skipped)} duplicate(s)[/dim]")
        if total_errors:
            console.print(f"[yellow]Warning:[/yellow] {len(total_errors)} lines could not be parsed")
            for line_num, line_text, error in total_errors[:5]:
                console.print(f"  Line {line_num}: {error}")


@obsidian_app.command(name="check")
def check_conflicts(
    ctx: typer.Context,
) -> None:
    """Check for conflicts between frontmatter and Obsidian Tasks lines.

    This command reads task files and compares the YAML frontmatter
    with any Obsidian Tasks format line in the content body.
    """
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=storage_format)
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
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=storage_format)
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
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=storage_format)
    formatter = ObsidianTasksFormat()

    task = manager.get(task_id)
    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    line = formatter.to_obsidian_line(task)
    console.print(line)
