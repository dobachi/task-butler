"""Task analysis engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import AIProvider, AnalysisResult

if TYPE_CHECKING:
    from ..models.task import Task


class TaskAnalyzer:
    """Analyzes tasks and provides priority scores with reasoning."""

    def __init__(self, provider: AIProvider | None = None):
        """Initialize the analyzer.

        Args:
            provider: AI provider to use. If None, uses config setting.
        """
        if provider is None:
            from . import get_provider
            provider = get_provider()
        self.provider = provider

    def analyze(self, task: "Task", all_tasks: list["Task"]) -> AnalysisResult:
        """Analyze a single task.

        Args:
            task: The task to analyze
            all_tasks: All tasks for context

        Returns:
            AnalysisResult with score, reasoning, and suggestions
        """
        return self.provider.analyze_task(task, all_tasks)

    def analyze_all(
        self, tasks: list["Task"], include_closed: bool = False
    ) -> list[AnalysisResult]:
        """Analyze all tasks and return sorted results.

        Args:
            tasks: List of tasks to analyze
            include_closed: Whether to include done/cancelled tasks

        Returns:
            List of AnalysisResult sorted by score (highest first)
        """
        # Filter tasks
        if include_closed:
            target_tasks = tasks
        else:
            target_tasks = [t for t in tasks if t.is_open]

        if not target_tasks:
            return []

        # Analyze each task
        results = [self.analyze(task, tasks) for task in target_tasks]

        # Sort by score (highest first)
        results.sort(key=lambda r: r.score, reverse=True)

        return results

    def get_top_priorities(
        self, tasks: list["Task"], count: int = 5
    ) -> list[tuple["Task", AnalysisResult]]:
        """Get the top priority tasks.

        Args:
            tasks: List of tasks to analyze
            count: Number of top tasks to return

        Returns:
            List of (task, analysis) tuples sorted by priority
        """
        results = self.analyze_all(tasks, include_closed=False)

        # Build task lookup
        task_map = {t.id: t for t in tasks}

        # Return top N with their tasks
        top = []
        for result in results[:count]:
            if result.task_id in task_map:
                top.append((task_map[result.task_id], result))

        return top
