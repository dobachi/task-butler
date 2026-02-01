"""Obsidian integration commands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from ...core.task_manager import TaskManager
from ...models.enums import Priority, Status
from ...models.task import Task
from ...storage import AmbiguousTaskIdError
from ...storage.obsidian import ObsidianTasksFormat, ParsedObsidianTask

console = Console()


class LinkFormat(str, Enum):
    """Link format for source replacement."""

    WIKI = "wiki"  # [[path|title]] format
    EMBED = "embed"  # ![[path|title]] format


@dataclass
class ImportedTaskInfo:
    """Information about an imported task for link replacement."""

    task: Task
    line_number: int
    original_line: str


def find_vault_root(path: Path) -> Path | None:
    """Find Obsidian vault root by looking for .obsidian directory.

    Args:
        path: Starting path to search from.

    Returns:
        Path to vault root, or None if not found.
    """
    current = path.resolve()
    if current.is_file():
        current = current.parent

    while current != current.parent:
        if (current / ".obsidian").is_dir():
            return current
        current = current.parent
    return None


def generate_wiki_link(
    task: Task,
    storage_dir: Path,
    vault_root: Path,
    link_format: LinkFormat = LinkFormat.WIKI,
    organization: str = "flat",
    kanban_dirs: dict[str, str] | None = None,
) -> str:
    """Generate an Obsidian wiki link for a task.

    Args:
        task: The task to generate a link for.
        storage_dir: Path to the task storage directory.
        vault_root: Path to the Obsidian vault root.
        link_format: Wiki link format (wiki or embed).
        organization: Organization method ("flat" or "kanban").
        kanban_dirs: Custom directory names for Kanban mode.

    Returns:
        Obsidian wiki link string.
    """
    from ...storage.markdown import MarkdownStorage

    # Generate the task filename with proper organization settings
    storage = MarkdownStorage(storage_dir, organization=organization, kanban_dirs=kanban_dirs)
    filename = storage._task_filename(task.id, task.title)

    # Get the correct directory based on task status (for kanban mode)
    status_dir = storage._get_status_dir(task.status)
    task_file_path = status_dir / filename

    try:
        relative_path = task_file_path.relative_to(vault_root)
        # Remove .md extension for Obsidian links
        link_path = str(relative_path).replace("\\", "/")
        if link_path.endswith(".md"):
            link_path = link_path[:-3]
    except ValueError:
        # Storage is outside vault - use absolute path (won't work in Obsidian)
        link_path = str(task_file_path)

    # Generate link
    prefix = "!" if link_format == LinkFormat.EMBED else ""
    return f"{prefix}[[{link_path}|{task.title}]]"


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
    context_settings={"help_option_names": ["-h", "--help"]},
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
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks"),
) -> None:
    """Export tasks in Obsidian-compatible format."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
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
        console.print("[dim]Use --storage-dir to specify Obsidian vault location.[/dim]")
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


def _collect_files(
    path: Path,
    recursive: bool,
    pattern: str,
    exclude_dir: Path | None = None,
) -> list[Path]:
    """Collect markdown files from a path.

    Args:
        path: File or directory path
        recursive: Include subdirectories
        pattern: Glob pattern for file matching
        exclude_dir: Directory to exclude from collection

    Returns:
        List of file paths to process
    """
    if path.is_file():
        return [path]

    if recursive:
        files = list(path.rglob(pattern))
    else:
        files = list(path.glob(pattern))

    result = [f for f in files if f.is_file()]

    # Exclude storage directory if provided
    if exclude_dir and exclude_dir.exists():
        exclude_dir_resolved = exclude_dir.resolve()
        result = [f for f in result if not f.resolve().is_relative_to(exclude_dir_resolved)]

    return sorted(result)


def _prompt_duplicate_action(existing_task: Task, parsed: ParsedObsidianTask) -> str:
    """Prompt user for action on duplicate task.

    Args:
        existing_task: The existing task in storage
        parsed: The parsed task from Obsidian

    Returns:
        User's choice: 's' (skip), 'u' (update), 'f' (force), 'a' (all skip), 'A' (all update)
    """
    console.print(f'\n[yellow]⚠ Duplicate found:[/yellow] "{parsed.title}"')
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
    vault_root: Path | None = None,
    source_file_relative: str | None = None,
) -> tuple[list, list, list, list, list[ImportedTaskInfo]]:
    """Import tasks from a single file.

    Args:
        file: File path to import
        manager: TaskManager instance
        formatter: ObsidianTasksFormat instance
        duplicate_action: How to handle duplicates
        dry_run: Preview only
        global_action: Mutable dict for storing user's "all" choice
        vault_root: Obsidian vault root path (for source tracking)
        source_file_relative: Relative path from vault root (for source tracking)

    Returns:
        Tuple of (imported, updated, skipped, errors, imported_task_info) lists
    """
    content = file.read_text(encoding="utf-8")
    lines = content.split("\n")

    imported = []
    updated = []
    skipped = []
    errors = []
    imported_task_info: list[ImportedTaskInfo] = []

    for i, line in enumerate(lines, 1):
        original_line = line
        line = line.strip()
        # Check for Obsidian Tasks checkbox format: - [ ] or - [x] or - [X]
        # Skip regular wiki links like - [[...]] which also start with "- ["
        if not (
            line.startswith("- [ ] ") or line.startswith("- [x] ") or line.startswith("- [X] ")
        ):
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
                        # Track for link replacement even in dry-run
                        imported_task_info.append(
                            ImportedTaskInfo(
                                task=existing,
                                line_number=i,
                                original_line=original_line,
                            )
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

                        # Track for link replacement
                        imported_task_info.append(
                            ImportedTaskInfo(
                                task=existing,
                                line_number=i,
                                original_line=original_line,
                            )
                        )
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

                # Set source tracking if vault_root is provided
                if source_file_relative:
                    task.source_file = source_file_relative
                    task.source_line = i

                # Set obsidian_has_created based on whether source had ➕
                task.obsidian_has_created = parsed.created_at is not None
                if parsed.created_at:
                    task.created_at = parsed.created_at

                manager.repository.update(task)

                # Update status if completed
                if parsed.is_completed:
                    manager.complete(task.id)
                    if parsed.completed_at:
                        task = manager.get(task.id)
                        if task:
                            task.completed_at = parsed.completed_at
                            manager.repository.update(task)

                # Track for link replacement
                imported_task_info.append(
                    ImportedTaskInfo(
                        task=task,
                        line_number=i,
                        original_line=original_line,
                    )
                )
                imported.append(task)

        except ValueError as e:
            errors.append((i, line, str(e)))

    return imported, updated, skipped, errors, imported_task_info


def _replace_lines_with_links(
    file: Path,
    task_infos: list[ImportedTaskInfo],
    storage_dir: Path,
    vault_root: Path,
    link_format: LinkFormat,
    organization: str = "flat",
    kanban_dirs: dict[str, str] | None = None,
) -> None:
    """Replace task lines in a file with wiki links.

    Args:
        file: File to modify
        task_infos: List of imported task info with line numbers
        storage_dir: Path to task storage directory
        vault_root: Path to vault root
        link_format: Link format (wiki or embed)
        organization: Organization method ("flat" or "kanban")
        kanban_dirs: Custom directory names for Kanban mode
    """
    content = file.read_text(encoding="utf-8")
    lines = content.split("\n")

    # Sort by line number descending to replace from bottom up
    # (so line numbers don't shift as we replace)
    sorted_infos = sorted(task_infos, key=lambda x: x.line_number, reverse=True)

    for info in sorted_infos:
        line_idx = info.line_number - 1  # Convert to 0-indexed
        if 0 <= line_idx < len(lines):
            # Generate wiki link
            link = generate_wiki_link(
                info.task, storage_dir, vault_root, link_format, organization, kanban_dirs
            )
            # Preserve leading whitespace from original line
            original = info.original_line
            leading_whitespace = original[: len(original) - len(original.lstrip())]
            lines[line_idx] = f"{leading_whitespace}- {link}"

    # Write back
    file.write_text("\n".join(lines), encoding="utf-8")


@obsidian_app.command(name="import")
def import_tasks(
    ctx: typer.Context,
    path: Path = typer.Argument(..., help="File or directory to import from"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Include subdirectories"),
    pattern: str = typer.Option(
        "*.md", "--pattern", "-p", help="File pattern for directory import"
    ),
    skip: bool = typer.Option(False, "--skip", help="Skip duplicate tasks (default behavior)"),
    update: bool = typer.Option(False, "--update", help="Update existing tasks on duplicate"),
    force: bool = typer.Option(False, "--force", help="Force create even if duplicate exists"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Prompt for each duplicate"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be imported without making changes"
    ),
    link: bool = typer.Option(
        False, "--link", "-l", help="Replace source lines with wiki links to created tasks"
    ),
    link_format_opt: str = typer.Option(
        "wiki",
        "--link-format",
        help="Link format: 'wiki' ([[path|title]]) or 'embed' (![[path|title]])",
    ),
    vault_root_opt: Optional[Path] = typer.Option(
        None,
        "--vault-root",
        "-v",
        help="Obsidian vault root (auto-detected if not specified)",
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

        # Replace source lines with links
        task-butler obsidian import ~/Vault/daily/ --link

        # Use embed format for links
        task-butler obsidian import ~/Vault/daily/ --link --link-format embed
    """
    if not path.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    # Parse link format
    try:
        link_format = LinkFormat(link_format_opt.lower())
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid link format: {link_format_opt}")
        console.print("Use 'wiki' or 'embed'")
        raise typer.Exit(1)

    # Determine duplicate action (mutually exclusive options)
    action_count = sum([skip, update, force, interactive])
    if action_count > 1:
        console.print(
            "[red]Error:[/red] Options --skip, --update, --force, --interactive are mutually exclusive"
        )
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
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
    formatter = ObsidianTasksFormat()

    # Find vault root: CLI option > config > auto-detect
    vault_root = config.get_vault_root(vault_root_opt)
    if vault_root is None and link:
        vault_root = find_vault_root(path)
    if link and vault_root is None:
        console.print("[red]Error:[/red] Could not find Obsidian vault root (.obsidian directory)")
        console.print("[dim]Specify with --vault-root or set obsidian.vault_root in config[/dim]")
        raise typer.Exit(1)

        # Check if storage is inside the vault
        try:
            storage_dir.resolve().relative_to(vault_root.resolve())
        except ValueError:
            console.print("[yellow]Warning:[/yellow] Task storage is outside the vault")
            console.print(f"  Vault root: {vault_root}")
            console.print(f"  Storage: {storage_dir}")
            console.print("[dim]Links may not work correctly in Obsidian[/dim]")

        if dry_run:
            console.print(f"[dim]Vault root: {vault_root}[/dim]")
            console.print(f"[dim]Storage: {storage_dir}[/dim]")

    # Collect files to process, excluding storage directory
    files = _collect_files(path, recursive, pattern, exclude_dir=storage_dir)

    # Show message if storage directory is being excluded
    if storage_dir.exists() and path.is_dir() and recursive:
        try:
            storage_dir.resolve().relative_to(path.resolve())
            console.print(f"[dim](excluding storage directory: {storage_dir})[/dim]")
        except ValueError:
            pass  # storage_dir is not under import path

    if not files:
        console.print(f"[yellow]No files found matching pattern '{pattern}' in {path}[/yellow]")
        return

    if path.is_dir():
        console.print(f"[bold]Processing {len(files)} file(s) from {path}[/bold]")
        if recursive:
            console.print("[dim](recursive mode)[/dim]")

    total_imported = []
    total_updated = []
    total_skipped = []
    total_errors = []
    total_task_infos: dict[Path, list[ImportedTaskInfo]] = {}
    global_action: dict = {}  # For storing "all skip" or "all update" choice

    for file in files:
        if len(files) > 1:
            console.print(f"\n[cyan]{file.name}:[/cyan]")

        # Calculate relative path from vault root for source tracking
        source_file_relative: str | None = None
        if vault_root:
            try:
                source_file_relative = str(file.resolve().relative_to(vault_root.resolve()))
            except ValueError:
                pass

        imported, updated, skipped, errors, task_infos = _import_single_file(
            file,
            manager,
            formatter,
            duplicate_action,
            dry_run,
            global_action,
            vault_root=vault_root,
            source_file_relative=source_file_relative,
        )

        total_imported.extend(imported)
        total_updated.extend(updated)
        total_skipped.extend(skipped)
        total_errors.extend(errors)
        if task_infos:
            total_task_infos[file] = task_infos

    # Replace source lines with links if requested
    if link and total_task_infos and not dry_run:
        for file, task_infos in total_task_infos.items():
            _replace_lines_with_links(
                file, task_infos, storage_dir, vault_root, link_format, organization, kanban_dirs
            )
        console.print(
            f"[green]✓[/green] Replaced {sum(len(t) for t in total_task_infos.values())} "
            f"task line(s) with links"
        )

    # Summary
    console.print()
    if dry_run:
        console.print("[bold]Dry run summary:[/bold]")
        console.print(f"  Would import: {len(total_imported)} new task(s)")
        if total_updated:
            console.print(f"  Would update: {len(total_updated)} existing task(s)")
        if total_skipped:
            console.print(f"  Would skip: {len(total_skipped)} duplicate(s)")
        if link and total_task_infos:
            total_links = sum(len(t) for t in total_task_infos.values())
            console.print(f"  Would replace: {total_links} line(s) with links")
        if total_errors:
            console.print(f"  [yellow]Parse errors: {len(total_errors)}[/yellow]")
    else:
        console.print(f"[green]✓[/green] Imported {len(total_imported)} new task(s)")
        if total_updated:
            console.print(f"[blue]✓[/blue] Updated {len(total_updated)} existing task(s)")
        if total_skipped:
            console.print(f"[dim]Skipped {len(total_skipped)} duplicate(s)[/dim]")
        if total_errors:
            console.print(
                f"[yellow]Warning:[/yellow] {len(total_errors)} lines could not be parsed"
            )
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
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
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
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
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
            from ...models.enums import Status

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
    task_id: str = typer.Argument(..., help="Task ID (full or short)"),
) -> None:
    """Display a task in Obsidian Tasks format.

    Useful for copying the task line to paste into Obsidian notes.
    """
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
    formatter = ObsidianTasksFormat()

    try:
        task = manager.get(task_id)
    except AmbiguousTaskIdError as e:
        console.print(f"[red]Error:[/red] Ambiguous task ID '{e.task_id}'")
        console.print("Matching tasks:")
        for t in e.matches:
            console.print(f"  {t.short_id} - {t.title}")
        raise typer.Exit(1)

    if not task:
        console.print(f"[red]Error:[/red] Task not found: {task_id}")
        raise typer.Exit(1)

    line = formatter.to_obsidian_line(task)
    console.print(line)


@obsidian_app.command(name="fix-created")
def fix_created(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be changed without making changes"
    ),
    vault_root_opt: Optional[Path] = typer.Option(
        None,
        "--vault-root",
        "-v",
        help="Obsidian vault root (auto-detected if not specified)",
    ),
) -> None:
    """Fix obsidian_has_created for imported tasks.

    Checks tasks that have source_file set and updates obsidian_has_created
    based on whether the original source had ➕ (created date).

    This is useful to fix tasks that were imported before this feature was added.

    Examples:
        # Preview changes
        task-butler obsidian fix-created --dry-run

        # Apply fixes
        task-butler obsidian fix-created
    """
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )
    formatter = ObsidianTasksFormat()

    # Find vault root
    vault_root = config.get_vault_root(vault_root_opt)
    if vault_root is None:
        vault_root = find_vault_root(storage_dir)

    if vault_root is None:
        console.print("[red]Error:[/red] Could not find Obsidian vault root (.obsidian directory)")
        console.print("[dim]Specify with --vault-root or set obsidian.vault_root in config[/dim]")
        raise typer.Exit(1)

    # Get all tasks with source_file
    all_tasks = manager.list(include_done=True)
    imported_tasks = [t for t in all_tasks if t.source_file]

    if not imported_tasks:
        console.print("[dim]No imported tasks found (no tasks with source_file)[/dim]")
        return

    console.print(f"[bold]Checking {len(imported_tasks)} imported task(s)...[/bold]")
    if dry_run:
        console.print("[dim](dry run mode)[/dim]")

    fixed_count = 0
    error_count = 0

    for task in imported_tasks:
        source_path = vault_root / task.source_file
        if not source_path.exists():
            console.print(
                f"[yellow]⚠[/yellow] {task.short_id}: Source file not found: {task.source_file}"
            )
            error_count += 1
            continue

        # Read source file and find the original line
        try:
            content = source_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Find the task line
            original_line = None
            if task.source_line and 1 <= task.source_line <= len(lines):
                original_line = lines[task.source_line - 1].strip()
            else:
                # Search for matching task title
                for line in lines:
                    stripped = line.strip()
                    if (
                        stripped.startswith("- [ ]") or stripped.lower().startswith("- [x]")
                    ) and task.title in stripped:
                        original_line = stripped
                        break

            if not original_line:
                console.print(
                    f"[yellow]⚠[/yellow] {task.short_id}: Could not find task line in source"
                )
                error_count += 1
                continue

            # Check if original line has ➕
            has_created_in_source = "➕" in original_line

            # Only fix if there's a mismatch
            if task.obsidian_has_created != has_created_in_source:
                if dry_run:
                    action = "would add ➕" if has_created_in_source else "would remove ➕"
                    console.print(f"  [blue]FIX[/blue] {task.short_id}: {task.title} ({action})")
                else:
                    task.obsidian_has_created = has_created_in_source
                    # Also update created_at if source has it
                    if has_created_in_source:
                        try:
                            parsed = formatter.from_obsidian_line(original_line)
                            if parsed.created_at:
                                task.created_at = parsed.created_at
                        except ValueError:
                            pass
                    manager.repository.update(task)
                    action = "added ➕" if has_created_in_source else "removed ➕"
                    console.print(f"  [green]✓[/green] {task.short_id}: {task.title} ({action})")
                fixed_count += 1

        except Exception as e:
            console.print(f"[red]✗[/red] {task.short_id}: Error reading source: {e}")
            error_count += 1

    # Summary
    console.print()
    if fixed_count == 0 and error_count == 0:
        console.print("[green]✓[/green] All imported tasks already have correct settings")
    else:
        action = "Would fix" if dry_run else "Fixed"
        console.print(f"[bold]{action} {fixed_count} task(s)[/bold]")
        if error_count > 0:
            console.print(f"[yellow]Errors: {error_count}[/yellow]")


@obsidian_app.command(name="fix-links")
def fix_links(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be changed without making changes"
    ),
    vault_root_opt: Optional[Path] = typer.Option(
        None,
        "--vault-root",
        "-v",
        help="Obsidian vault root (auto-detected if not specified)",
    ),
    link_format_opt: str = typer.Option(
        "wiki",
        "--link-format",
        help="Link format: 'wiki' ([[path|title]]) or 'embed' (![[path|title]])",
    ),
) -> None:
    """Fix wiki links in source files for imported tasks.

    Regenerates wiki links with correct paths (e.g., for Kanban subdirectories)
    and updates the source files.

    This is useful to fix links that were created before Kanban support was added.

    Examples:
        # Preview changes
        task-butler obsidian fix-links --dry-run

        # Apply fixes
        task-butler obsidian fix-links
    """
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    storage_format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=storage_format, organization=organization, kanban_dirs=kanban_dirs
    )

    # Parse link format
    try:
        link_format = LinkFormat(link_format_opt.lower())
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid link format: {link_format_opt}")
        console.print("Use 'wiki' or 'embed'")
        raise typer.Exit(1)

    # Find vault root
    vault_root = config.get_vault_root(vault_root_opt)
    if vault_root is None:
        vault_root = find_vault_root(storage_dir)

    if vault_root is None:
        console.print("[red]Error:[/red] Could not find Obsidian vault root (.obsidian directory)")
        console.print("[dim]Specify with --vault-root or set obsidian.vault_root in config[/dim]")
        raise typer.Exit(1)

    # Get all tasks with source_file
    all_tasks = manager.list(include_done=True)
    imported_tasks = [t for t in all_tasks if t.source_file]

    if not imported_tasks:
        console.print("[dim]No imported tasks found (no tasks with source_file)[/dim]")
        return

    console.print(f"[bold]Checking {len(imported_tasks)} imported task(s)...[/bold]")
    if dry_run:
        console.print("[dim](dry run mode)[/dim]")

    fixed_count = 0
    error_count = 0

    # Group tasks by source file
    tasks_by_file: dict[str, list[Task]] = {}
    for task in imported_tasks:
        if task.source_file not in tasks_by_file:
            tasks_by_file[task.source_file] = []
        tasks_by_file[task.source_file].append(task)

    for source_file_rel, tasks in tasks_by_file.items():
        source_path = vault_root / source_file_rel
        if not source_path.exists():
            console.print(f"[yellow]⚠[/yellow] Source file not found: {source_file_rel}")
            error_count += len(tasks)
            continue

        try:
            content = source_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            modified = False

            for task in tasks:
                # Generate correct link
                correct_link = generate_wiki_link(
                    task, storage_dir, vault_root, link_format, organization, kanban_dirs
                )

                # Find line with wiki link to this task
                for i, line in enumerate(lines):
                    # Check if this line contains a wiki link to this task
                    # Link format: - [[path|title]] or - ![[path|title]]
                    if f"|{task.title}]]" in line and line.strip().startswith("- "):
                        # Extract existing link
                        import re

                        link_match = re.search(r"(!?\[\[[^\]]+\]\])", line)
                        if link_match:
                            existing_link = link_match.group(1)
                            if existing_link != correct_link:
                                if dry_run:
                                    console.print(
                                        f"  [blue]FIX[/blue] {task.short_id}: {task.title}"
                                    )
                                    console.print(f"    [dim]Old: {existing_link}[/dim]")
                                    console.print(f"    [dim]New: {correct_link}[/dim]")
                                else:
                                    # Replace the link
                                    lines[i] = line.replace(existing_link, correct_link)
                                    modified = True
                                    console.print(
                                        f"  [green]✓[/green] {task.short_id}: {task.title}"
                                    )
                                fixed_count += 1
                        break

            if modified and not dry_run:
                source_path.write_text("\n".join(lines), encoding="utf-8")

        except Exception as e:
            console.print(f"[red]✗[/red] Error processing {source_file_rel}: {e}")
            error_count += 1

    # Summary
    console.print()
    if fixed_count == 0 and error_count == 0:
        console.print("[green]✓[/green] All links are already correct")
    else:
        action = "Would fix" if dry_run else "Fixed"
        console.print(f"[bold]{action} {fixed_count} link(s)[/bold]")
        if error_count > 0:
            console.print(f"[yellow]Errors: {error_count}[/yellow]")
