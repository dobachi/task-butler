"""Analyze command for AI-powered task analysis."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def analyze_tasks(
    ctx: typer.Context,
    task_id: Optional[str] = typer.Argument(
        None, help="Task ID to analyze (analyzes all if not specified)"
    ),
    count: int = typer.Option(10, "--count", "-n", help="Number of tasks to show"),
    save: bool = typer.Option(False, "--save", "-s", help="Save analysis results to tasks"),
    table: bool = typer.Option(False, "--table", "-t", help="Show as table"),
) -> None:
    """Analyze tasks and show priority scores with reasoning.

    Uses AI to analyze task priority based on:
    - Deadline urgency
    - Dependency impact (how many tasks are blocked)
    - Effort/complexity
    - How long the task has been open
    - Explicit priority setting
    """
    from ...ai.analyzer import TaskAnalyzer
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
    analyzer = TaskAnalyzer()

    # Get all tasks
    all_tasks = manager.list(include_done=False)

    if not all_tasks:
        console.print("[dim]No open tasks to analyze[/dim]")
        raise typer.Exit(0)

    if task_id:
        # Analyze single task
        task = manager.get(task_id)
        if not task:
            console.print(f"[red]Task not found: {task_id}[/red]")
            raise typer.Exit(1)

        result = analyzer.analyze(task, all_tasks)
        _show_single_analysis(task, result)

        if save:
            # Save analysis to task notes
            note = f"AI分析スコア: {result.score}/100 - {result.reasoning}"
            manager.add_note(task.id, note)
            console.print("[green]✓[/green] Analysis saved to task notes")
    else:
        # Analyze all tasks
        results = analyzer.analyze_all(all_tasks)[:count]

        if table:
            _show_analysis_table(results, all_tasks)
        else:
            _show_analysis_list(results, all_tasks)

        if save:
            # Save all analyses
            task_map = {t.id: t for t in all_tasks}
            for result in results:
                if result.task_id in task_map:
                    note = f"AI分析スコア: {result.score}/100 - {result.reasoning}"
                    manager.add_note(result.task_id, note)
            console.print(f"\n[green]✓[/green] Analysis saved to {len(results)} tasks")


def _show_single_analysis(task, result) -> None:
    """Show detailed analysis for a single task."""
    from ...models.enums import Priority

    priority_icons = {
        Priority.URGENT: "🔺",
        Priority.HIGH: "⏫",
        Priority.MEDIUM: "🔼",
        Priority.LOW: "🔽",
        Priority.LOWEST: "⏬",
    }

    console.print()
    console.print("[bold]📊 タスク分析[/bold]")
    console.print()

    icon = priority_icons.get(task.priority, "🔼")
    console.print(f"[bold]{icon} {task.title}[/bold] ({task.short_id})")
    console.print()

    # Score with color
    score = result.score
    if score >= 80:
        score_color = "red"
    elif score >= 60:
        score_color = "yellow"
    elif score >= 40:
        score_color = "green"
    else:
        score_color = "dim"

    console.print(f"スコア: [{score_color}]{score:.1f}/100[/{score_color}] ({result.score_label})")
    console.print(f"理由: {result.reasoning}")

    if result.suggestions:
        console.print()
        console.print("[bold]提案:[/bold]")
        for suggestion in result.suggestions:
            console.print(f"  • {suggestion}")


def _show_analysis_list(results, all_tasks) -> None:
    """Show analysis results as a list."""
    from ...models.enums import Priority

    task_map = {t.id: t for t in all_tasks}

    priority_icons = {
        Priority.URGENT: "🔺",
        Priority.HIGH: "⏫",
        Priority.MEDIUM: "🔼",
        Priority.LOW: "🔽",
        Priority.LOWEST: "⏬",
    }

    console.print()
    console.print("[bold]📊 タスク分析結果[/bold]")
    console.print()

    for i, result in enumerate(results, 1):
        task = task_map.get(result.task_id)
        if not task:
            continue

        icon = priority_icons.get(task.priority, "🔼")

        # Score color
        if result.score >= 80:
            score_color = "red"
        elif result.score >= 60:
            score_color = "yellow"
        elif result.score >= 40:
            score_color = "green"
        else:
            score_color = "dim"

        console.print(f"{i}. {icon} [bold]{task.title}[/bold] ({task.short_id})")
        console.print(
            f"   スコア: [{score_color}]{result.score:.1f}[/{score_color}] - {result.reasoning}"
        )
        console.print()


def _show_analysis_table(results, all_tasks) -> None:
    """Show analysis results as a table."""
    from ...models.enums import Priority

    task_map = {t.id: t for t in all_tasks}

    priority_labels = {
        Priority.URGENT: "urgent",
        Priority.HIGH: "high",
        Priority.MEDIUM: "medium",
        Priority.LOW: "low",
        Priority.LOWEST: "lowest",
    }

    table = Table(title="📊 タスク分析結果")
    table.add_column("#", style="dim", width=3)
    table.add_column("スコア", justify="right", width=8)
    table.add_column("優先度", width=8)
    table.add_column("タスク", width=30)
    table.add_column("理由", width=40)

    for i, result in enumerate(results, 1):
        task = task_map.get(result.task_id)
        if not task:
            continue

        # Score color
        if result.score >= 80:
            score_str = f"[red]{result.score:.1f}[/red]"
        elif result.score >= 60:
            score_str = f"[yellow]{result.score:.1f}[/yellow]"
        elif result.score >= 40:
            score_str = f"[green]{result.score:.1f}[/green]"
        else:
            score_str = f"[dim]{result.score:.1f}[/dim]"

        priority = priority_labels.get(task.priority, "medium")

        table.add_row(
            str(i),
            score_str,
            priority,
            f"{task.title} ({task.short_id})",
            result.reasoning,
        )

    console.print()
    console.print(table)
