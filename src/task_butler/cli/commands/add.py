"""Add task command."""

from __future__ import annotations

from datetime import datetime, timedelta
import re
from typing import Optional

import typer
from rich.console import Console

from ...core.task_manager import TaskManager
from ...models.task import RecurrenceRule
from ...models.enums import Priority, Frequency

console = Console()


def parse_due_date(value: str) -> datetime:
    """Parse due date from string."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d",
        "%m-%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            # If year not specified, use current year
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now().year)
            return dt
        except ValueError:
            continue

    # Try relative dates
    value_lower = value.lower()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if value_lower == "today":
        return today
    elif value_lower == "tomorrow":
        return today + timedelta(days=1)
    elif value_lower == "next week":
        return today + timedelta(weeks=1)

    raise typer.BadParameter(f"Invalid date format: {value}")


def parse_recurrence(value: str) -> RecurrenceRule:
    """Parse recurrence rule from string."""
    value_lower = value.lower()

    if value_lower == "daily":
        return RecurrenceRule(frequency=Frequency.DAILY)
    elif value_lower == "weekly":
        return RecurrenceRule(frequency=Frequency.WEEKLY)
    elif value_lower == "monthly":
        return RecurrenceRule(frequency=Frequency.MONTHLY)
    elif value_lower == "yearly":
        return RecurrenceRule(frequency=Frequency.YEARLY)

    # Try "every N days/weeks/months"
    match = re.match(r"every\s+(\d+)\s+(day|week|month|year)s?", value_lower)
    if match:
        interval = int(match.group(1))
        unit = match.group(2)
        freq_map = {
            "day": Frequency.DAILY,
            "week": Frequency.WEEKLY,
            "month": Frequency.MONTHLY,
            "year": Frequency.YEARLY,
        }
        return RecurrenceRule(frequency=freq_map[unit], interval=interval)

    raise typer.BadParameter(f"Invalid recurrence format: {value}")


def add_task(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Task title"),
    description: Optional[str] = typer.Option(
        None, "--desc", "-D", help="Task description"
    ),
    priority: Priority = typer.Option(
        Priority.MEDIUM, "--priority", "-p", help="Task priority"
    ),
    due: Optional[str] = typer.Option(
        None, "--due", "-d", help="Due date (YYYY-MM-DD, today, tomorrow)"
    ),
    scheduled: Optional[str] = typer.Option(
        None, "--scheduled", "-s", help="Scheduled date - when to work on it (YYYY-MM-DD, today, tomorrow)"
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date - when work can begin (YYYY-MM-DD, today, tomorrow)"
    ),
    tags: Optional[str] = typer.Option(
        None, "--tags", "-t", help="Comma-separated tags"
    ),
    project: Optional[str] = typer.Option(
        None, "--project", "-P", help="Project name"
    ),
    parent: Optional[str] = typer.Option(
        None, "--parent", help="Parent task ID"
    ),
    depends: Optional[str] = typer.Option(
        None, "--depends", help="Comma-separated dependency task IDs"
    ),
    hours: Optional[float] = typer.Option(
        None, "--hours", "-h", help="Estimated hours"
    ),
    recur: Optional[str] = typer.Option(
        None, "--recur", "-r", help="Recurrence (daily, weekly, monthly, yearly, or 'every N days')"
    ),
) -> None:
    """Add a new task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    manager = TaskManager(storage_dir, format=format)

    try:
        # Parse optional fields
        due_date = parse_due_date(due) if due else None
        scheduled_date = parse_due_date(scheduled) if scheduled else None
        start_date = parse_due_date(start) if start else None
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        dep_list = [d.strip() for d in depends.split(",")] if depends else None
        recurrence = parse_recurrence(recur) if recur else None

        task = manager.add(
            title=title,
            description=description or "",
            priority=priority,
            due_date=due_date,
            scheduled_date=scheduled_date,
            start_date=start_date,
            tags=tag_list,
            project=project,
            parent_id=parent,
            dependencies=dep_list,
            estimated_hours=hours,
            recurrence=recurrence,
        )

        console.print(f"[green]✓[/green] Created task: [bold]{task.title}[/bold]")
        console.print(f"  ID: [cyan]{task.short_id}[/cyan]")

        if task.due_date:
            console.print(f"  Due: {task.due_date.strftime('%Y-%m-%d')}")
        if task.scheduled_date:
            console.print(f"  Scheduled: {task.scheduled_date.strftime('%Y-%m-%d')}")
        if task.start_date:
            console.print(f"  Start: {task.start_date.strftime('%Y-%m-%d')}")
        if task.project:
            console.print(f"  Project: {task.project}")
        if task.recurrence:
            console.print(f"  Recurring: {task.recurrence.frequency.value}")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
