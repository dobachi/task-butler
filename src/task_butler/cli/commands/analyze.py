"""Analyze command for AI-powered task analysis."""

from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def analyze_tasks(
    ctx: typer.Context,
    task_id: Optional[str] = typer.Argument(
        None, help="Task ID to analyze (analyzes all if not specified)"
    ),
    count: int = typer.Option(10, "--count", "-n", help="Number of tasks to show"),
    individual: bool = typer.Option(
        False, "--individual", "-i", help="Individual analysis mode (analyze each task separately)"
    ),
    limit: int = typer.Option(
        20, "--limit", "-l", help="Maximum tasks for holistic analysis (default: 20)"
    ),
    save: bool = typer.Option(False, "--save", "-s", help="Save analysis results to tasks"),
    table: bool = typer.Option(False, "--table", "-t", help="Show as table (individual mode only)"),
) -> None:
    """Analyze tasks and show priority insights.

    Default mode: Holistic analysis (cross-task insights)
    Use --individual / -i for per-task analysis

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

    # Show AI provider info
    ai_provider = config.get_ai_provider()
    provider_labels = {
        "rule_based": "ルールベース",
        "llama": "ローカルLLM (llama)",
        "openai": "OpenAI API",
    }
    console.print(f"[dim]AIプロバイダー: {provider_labels.get(ai_provider, ai_provider)}[/dim]")

    # Get all tasks
    all_tasks = manager.list(include_done=False)

    if not all_tasks:
        console.print("[dim]No open tasks to analyze[/dim]")
        raise typer.Exit(0)

    if task_id:
        # Analyze single task (always individual mode)
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

    elif individual:
        # Individual analysis mode (legacy behavior)
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

    else:
        # Holistic analysis mode (default)
        holistic_result = analyzer.analyze_holistic(all_tasks, max_tasks=limit)
        _show_holistic_analysis(holistic_result, all_tasks)


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
    console.print("[bold]📊 タスク分析結果[/bold] [dim](個別分析モード)[/dim]")
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

    table = Table(title="📊 タスク分析結果 (個別分析モード)")
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


def _show_holistic_analysis(result, all_tasks) -> None:
    """Show holistic analysis results."""
    task_map = {t.id: t for t in all_tasks}

    console.print()
    console.print("[bold]📊 タスク全体分析[/bold]")
    console.print()

    # Show warnings first
    if result.warnings:
        for warning in result.warnings:
            console.print(f"[yellow]⚠️ {warning}[/yellow]")
        console.print()

    # Insights - show before assessment for context
    if result.insights:
        console.print("[bold cyan]【重要な洞察】[/bold cyan]")
        sorted_insights = sorted(result.insights, key=lambda x: x.priority)
        for insight in sorted_insights[:5]:
            icon = "💡"
            if insight.insight_type == "warning":
                icon = "⚠️"
            elif insight.insight_type == "blocker":
                icon = "🚫"
            elif insight.insight_type == "sequence":
                icon = "📋"
            elif insight.insight_type == "optimization":
                icon = "⏰"
            console.print(f"  {icon} {insight.description}")
        console.print()

    # Overall assessment
    if result.overall_assessment:
        console.print(Panel(result.overall_assessment, title="全体評価", border_style="blue"))
        console.print()

    # Recommended order with reasons (prefer ranked_tasks if available)
    if result.ranked_tasks:
        console.print("[bold cyan]【推奨実行順序】[/bold cyan]")
        for i, ranked in enumerate(result.ranked_tasks[:10], 1):
            task = task_map.get(ranked.task_id)
            if task:
                # Score color
                if ranked.score >= 80:
                    score_color = "red"
                elif ranked.score >= 60:
                    score_color = "yellow"
                elif ranked.score >= 40:
                    score_color = "green"
                else:
                    score_color = "dim"

                console.print(
                    f"  {i}. [{score_color}]{ranked.score:.0f}点[/{score_color}] "
                    f"[bold]{task.title}[/bold] ({task.short_id})"
                )
                console.print(f"     [dim]→ {ranked.reason}[/dim]")
        if len(result.ranked_tasks) > 10:
            console.print(f"  [dim]... 他 {len(result.ranked_tasks) - 10} 件[/dim]")
        console.print()
    elif result.recommended_order:
        # Fallback to simple list
        console.print("[bold cyan]【推奨実行順序】[/bold cyan]")
        for i, task_id in enumerate(result.recommended_order[:10], 1):
            task = task_map.get(task_id)
            if task:
                console.print(f"  {i}. [{task.short_id}] {task.title}")
        if len(result.recommended_order) > 10:
            console.print(f"  [dim]... 他 {len(result.recommended_order) - 10} 件[/dim]")
        console.print()

    # Task groups
    if result.task_groups:
        console.print("[bold cyan]【グルーピング提案】[/bold cyan]")
        for group_name, task_ids in result.task_groups[:5]:
            task_titles = []
            for tid in task_ids[:3]:
                task = task_map.get(tid)
                if task:
                    task_titles.append(task.title)
            titles_str = ", ".join(task_titles)
            if len(task_ids) > 3:
                titles_str += f" 他{len(task_ids) - 3}件"
            console.print(f"  📦 {group_name}: {titles_str}")
        console.print()

    # Footer with stats
    console.print(
        f"[dim]分析対象: {result.analyzed_tasks}/{result.total_tasks} タスク[/dim]"
    )
    console.print()
    console.print("[dim]個別分析は 'tb analyze --individual' で実行できます[/dim]")
