"""Plan command for daily planning assistant."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def plan_day(
    ctx: typer.Context,
    date: Optional[str] = typer.Option(
        None, "--date", "-d", help="Target date (YYYY-MM-DD, default: today)"
    ),
    hours: float = typer.Option(8.0, "--hours", "-H", help="Working hours for the day"),
    start: str = typer.Option("09:00", "--start", "-s", help="Start time (HH:MM)"),
) -> None:
    """Create a daily work plan.

    Schedules tasks based on priority, estimated effort,
    and dependencies. Includes buffer time for interruptions.
    """
    from ...ai.planner import DailyPlanner
    from ...config import get_config
    from ...core.task_manager import TaskManager

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()

    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )

    # Parse date
    target_date = None
    if date:
        try:
            if date == "today":
                target_date = datetime.now()
            elif date == "tomorrow":
                from datetime import timedelta
                target_date = datetime.now() + timedelta(days=1)
            else:
                target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Invalid date format: {date}[/red]")
            console.print("Use: YYYY-MM-DD, today, or tomorrow")
            raise typer.Exit(1)
    else:
        target_date = datetime.now()

    # Create planner with settings
    planner = DailyPlanner(
        default_hours=hours,
        start_time=start,
    )

    # Get all open tasks
    all_tasks = manager.list(include_done=False)

    if not all_tasks:
        console.print("[dim]No open tasks to schedule[/dim]")
        raise typer.Exit(0)

    # Create plan
    plan = planner.create_plan(
        tasks=all_tasks,
        working_hours=hours,
        target_date=target_date,
    )

    # Display plan
    _display_plan(plan)


def _display_plan(plan) -> None:
    """Display the daily plan with rich formatting."""
    from ...models.enums import Priority

    priority_icons = {
        Priority.URGENT: "[red]🔺[/red]",
        Priority.HIGH: "[red]⏫[/red]",
        Priority.MEDIUM: "[yellow]🔼[/yellow]",
        Priority.LOW: "[green]🔽[/green]",
        Priority.LOWEST: "[dim]⏬[/dim]",
    }

    date_str = plan.date.strftime("%Y-%m-%d")
    weekday = ["月", "火", "水", "木", "金", "土", "日"][plan.date.weekday()]

    console.print()
    console.print(
        Panel.fit(
            f"[bold]📅 {date_str} ({weekday}) の作業計画[/bold]\n"
            f"作業時間: {plan.total_hours}時間 / バッファ: {plan.buffer_hours}時間",
            border_style="blue",
        )
    )

    # Morning slots
    if plan.morning_slots:
        morning_hours = sum(s.duration_hours for s in plan.morning_slots)
        console.print()
        console.print(f"[bold cyan]午前（{morning_hours:.1f}時間）[/bold cyan]")

        for slot in plan.morning_slots:
            task = slot.task
            icon = priority_icons.get(task.priority, "🔼")
            duration = f"{slot.duration_hours:.1f}h" if slot.duration_hours >= 1 else f"{int(slot.duration_hours * 60)}m"
            console.print(
                f"  {slot.start_time}-{slot.end_time} {icon} {task.title} ({duration})"
            )

    # Afternoon slots
    if plan.afternoon_slots:
        afternoon_hours = sum(s.duration_hours for s in plan.afternoon_slots)
        console.print()
        console.print(f"[bold cyan]午後（{afternoon_hours:.1f}時間）[/bold cyan]")

        for slot in plan.afternoon_slots:
            task = slot.task
            icon = priority_icons.get(task.priority, "🔼")
            duration = f"{slot.duration_hours:.1f}h" if slot.duration_hours >= 1 else f"{int(slot.duration_hours * 60)}m"
            console.print(
                f"  {slot.start_time}-{slot.end_time} {icon} {task.title} ({duration})"
            )

    # No tasks scheduled
    if not plan.morning_slots and not plan.afternoon_slots:
        console.print()
        console.print("[dim]スケジュール可能なタスクがありません[/dim]")

    # Warnings
    if plan.warnings:
        console.print()
        for warning in plan.warnings:
            console.print(f"[yellow]⚠️ {warning}[/yellow]")

    # Summary
    console.print()
    utilization = (plan.scheduled_hours / plan.total_hours) * 100 if plan.total_hours > 0 else 0
    console.print(
        f"[dim]スケジュール済み: {plan.scheduled_hours:.1f}h / {plan.total_hours}h "
        f"(稼働率: {utilization:.0f}%)[/dim]"
    )
