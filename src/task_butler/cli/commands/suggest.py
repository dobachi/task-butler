"""Suggest command for smart task recommendations."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console

console = Console()


def suggest_tasks(
    ctx: typer.Context,
    hours: Optional[float] = typer.Option(
        None, "--hours", "-H", help="Available working hours"
    ),
    energy: Optional[str] = typer.Option(
        None,
        "--energy",
        "-e",
        help="Energy level: low, medium, high",
    ),
    count: int = typer.Option(5, "--count", "-n", help="Number of suggestions"),
    quick: bool = typer.Option(
        False, "--quick", "-q", help="Show only quick tasks (< 30 min)"
    ),
) -> None:
    """Suggest which tasks to work on next.

    Considers:
    - Task priority and urgency
    - Available time
    - Energy level
    - Task dependencies
    """
    from ...ai.suggester import TaskSuggester
    from ...config import get_config
    from ...core.task_manager import TaskManager
    from ...models.enums import Priority

    config = get_config()
    storage_dir = config.get_storage_dir(ctx.obj.get("storage_dir") if ctx.obj else None)
    format = config.get_format(ctx.obj.get("format") if ctx.obj else None)
    organization = config.get_organization_method()
    kanban_dirs = config.get_kanban_dirs()

    manager = TaskManager(
        storage_dir, format=format, organization=organization, kanban_dirs=kanban_dirs
    )
    suggester = TaskSuggester()

    # Get all tasks
    all_tasks = manager.list(include_done=False)

    if not all_tasks:
        console.print("[dim]No open tasks[/dim]")
        raise typer.Exit(0)

    # Validate energy level
    if energy and energy not in ("low", "medium", "high"):
        console.print(f"[red]Invalid energy level: {energy}[/red]")
        console.print("Use: low, medium, or high")
        raise typer.Exit(1)

    # Get suggestions
    if quick:
        suggestions = suggester.suggest_quick_wins(all_tasks, max_minutes=30, count=count)
        title = "💡 クイックタスク（30分以内）"
    else:
        suggestions = suggester.suggest(
            tasks=all_tasks,
            hours_available=hours,
            energy_level=energy,  # type: ignore
            count=count,
        )
        if hours:
            title = f"💡 おすすめタスク（{hours}時間の作業時間）"
        elif energy:
            energy_labels = {"low": "低", "medium": "中", "high": "高"}
            title = f"💡 おすすめタスク（エネルギー: {energy_labels[energy]}）"
        else:
            title = "💡 おすすめタスク"

    if not suggestions:
        console.print("[dim]No matching tasks found[/dim]")
        raise typer.Exit(0)

    # Display suggestions
    priority_icons = {
        Priority.URGENT: "🔺",
        Priority.HIGH: "⏫",
        Priority.MEDIUM: "🔼",
        Priority.LOW: "🔽",
        Priority.LOWEST: "⏬",
    }

    console.print()
    console.print(f"[bold]{title}[/bold]")
    console.print()

    total_minutes = 0
    for i, suggestion in enumerate(suggestions, 1):
        task = suggestion.task
        icon = priority_icons.get(task.priority, "🔼")

        # Format time
        time_str = ""
        if suggestion.estimated_minutes:
            total_minutes += suggestion.estimated_minutes
            if suggestion.estimated_minutes >= 60:
                h = suggestion.estimated_minutes // 60
                m = suggestion.estimated_minutes % 60
                time_str = f"({h}h{m}m)" if m else f"({h}h)"
            else:
                time_str = f"({suggestion.estimated_minutes}m)"
        elif task.estimated_hours:
            mins = int(task.estimated_hours * 60)
            total_minutes += mins
            if task.estimated_hours >= 1:
                time_str = f"({task.estimated_hours}h)"
            else:
                time_str = f"({mins}m)"

        console.print(f"{i}. {icon} [bold]{task.title}[/bold] {time_str}")
        console.print(f"   {suggestion.reason}")
        console.print()

    # Show total time
    if total_minutes > 0:
        if total_minutes >= 60:
            h = total_minutes // 60
            m = total_minutes % 60
            time_str = f"{h}時間{m}分" if m else f"{h}時間"
        else:
            time_str = f"{total_minutes}分"
        console.print(f"[dim]合計見積: {time_str}[/dim]")
