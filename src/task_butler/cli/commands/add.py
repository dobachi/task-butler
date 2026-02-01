"""Add task command."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from ...core.task_manager import TaskManager
from ...models.enums import Frequency, Priority
from ...models.task import RecurrenceRule
from ..completion import complete_task_id
from ..date_picker import pick_date

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


def wizard_add(manager: TaskManager, initial_title: Optional[str] = None) -> None:
    """Interactive wizard for adding a task."""
    # 1. タイトル（必須）
    if initial_title:
        title = initial_title
        console.print(f"[bold]タスク名:[/bold] {title}")
    else:
        title = Prompt.ask("[bold]タスク名[/bold]")
        if not title:
            console.print("[red]タスク名は必須です[/red]")
            raise typer.Exit(1)

    # 2. 説明
    description = Prompt.ask("説明", default="")

    # 3. 優先度
    priority_str = Prompt.ask(
        "優先度",
        choices=["urgent", "high", "medium", "low", "lowest"],
        default="medium",
    )

    # 4. 期限 (カレンダー)
    console.print("\n[cyan]期限を設定しますか？[/cyan]")
    if Confirm.ask("カレンダーを開く", default=False):
        due_date = pick_date("期限")
    else:
        due_date = None

    # 5. 予定日 (カレンダー)
    console.print("\n[cyan]予定日を設定しますか？[/cyan]")
    if Confirm.ask("カレンダーを開く", default=False):
        scheduled_date = pick_date("予定日")
    else:
        scheduled_date = None

    # 6. 開始日 (カレンダー)
    console.print("\n[cyan]開始日を設定しますか？[/cyan]")
    if Confirm.ask("カレンダーを開く", default=False):
        start_date = pick_date("開始日")
    else:
        start_date = None

    # 7. タグ
    tags_str = Prompt.ask("タグ (カンマ区切り)", default="")
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

    # 8. プロジェクト
    project = Prompt.ask("プロジェクト", default="") or None

    # 9. 親タスク
    parent_id = Prompt.ask("親タスクID", default="") or None

    # 10. 依存タスク
    depends_str = Prompt.ask("依存タスクID (カンマ区切り)", default="")
    depends = [d.strip() for d in depends_str.split(",") if d.strip()] if depends_str else []

    # 11. 見積時間
    est_str = Prompt.ask("見積時間 (時間)", default="")
    estimated_hours = float(est_str) if est_str else None

    # 12. 繰り返し
    recurrence_str = (
        Prompt.ask(
            "繰り返し",
            choices=["", "daily", "weekly", "monthly", "yearly"],
            default="",
        )
        or None
    )

    # 確認表示
    console.print("\n[bold]--- タスク内容 ---[/bold]")
    console.print(f"タイトル: {title}")
    if description:
        console.print(f"説明: {description}")
    console.print(f"優先度: {priority_str}")
    if due_date:
        console.print(f"期限: {due_date}")
    if scheduled_date:
        console.print(f"予定日: {scheduled_date}")
    if start_date:
        console.print(f"開始日: {start_date}")
    if tags:
        console.print(f"タグ: {', '.join(tags)}")
    if project:
        console.print(f"プロジェクト: {project}")
    if parent_id:
        console.print(f"親タスク: {parent_id}")
    if depends:
        console.print(f"依存タスク: {', '.join(depends)}")
    if estimated_hours:
        console.print(f"見積時間: {estimated_hours}時間")
    if recurrence_str:
        console.print(f"繰り返し: {recurrence_str}")

    if Confirm.ask("\nこのタスクを作成しますか？", default=True):
        # Convert date to datetime if needed
        due_datetime = datetime.combine(due_date, datetime.min.time()) if due_date else None
        scheduled_datetime = (
            datetime.combine(scheduled_date, datetime.min.time()) if scheduled_date else None
        )
        start_datetime = datetime.combine(start_date, datetime.min.time()) if start_date else None

        # Parse recurrence
        recurrence = parse_recurrence(recurrence_str) if recurrence_str else None

        task = manager.add(
            title=title,
            description=description or "",
            priority=Priority(priority_str),
            due_date=due_datetime,
            scheduled_date=scheduled_datetime,
            start_date=start_datetime,
            tags=tags or None,
            project=project,
            parent_id=parent_id,
            dependencies=depends or None,
            estimated_hours=estimated_hours,
            recurrence=recurrence,
        )
        console.print(f"\n[green]✓ タスクを作成しました: {task.short_id}[/green]")
    else:
        console.print("[yellow]キャンセルしました[/yellow]")


def add_task(
    ctx: typer.Context,
    title: Optional[str] = typer.Argument(None, help="Task title"),
    wizard: bool = typer.Option(False, "--wizard", "-w", help="Interactive wizard mode"),
    description: Optional[str] = typer.Option(None, "--desc", "-D", help="Task description"),
    priority: Priority = typer.Option(Priority.MEDIUM, "--priority", "-p", help="Task priority"),
    due: Optional[str] = typer.Option(
        None, "--due", "-d", help="Due date (YYYY-MM-DD, today, tomorrow)"
    ),
    scheduled: Optional[str] = typer.Option(
        None,
        "--scheduled",
        "-s",
        help="Scheduled date - when to work on it (YYYY-MM-DD, today, tomorrow)",
    ),
    start: Optional[str] = typer.Option(
        None, "--start", help="Start date - when work can begin (YYYY-MM-DD, today, tomorrow)"
    ),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
    project: Optional[str] = typer.Option(None, "--project", "-P", help="Project name"),
    parent: Annotated[
        Optional[str],
        typer.Option("--parent", help="Parent task ID", autocompletion=complete_task_id),
    ] = None,
    depends: Annotated[
        Optional[str],
        typer.Option(
            "--depends", help="Comma-separated dependency task IDs", autocompletion=complete_task_id
        ),
    ] = None,
    hours: Optional[float] = typer.Option(None, "--hours", "-h", help="Estimated hours"),
    recur: Optional[str] = typer.Option(
        None, "--recur", "-r", help="Recurrence (daily, weekly, monthly, yearly, or 'every N days')"
    ),
) -> None:
    """Add a new task."""
    from ...config import get_config

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()
    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )

    if wizard:
        wizard_add(manager, title)
        return

    if not title:
        console.print("[red]Error: タイトルが必要です (--wizard で対話モード)[/red]")
        raise typer.Exit(1)

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
