"""Smart task suggestion engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .base import AIProvider, SuggestionResult

if TYPE_CHECKING:
    from ..models.task import Task

EnergyLevel = Literal["low", "medium", "high"]


class TaskSuggester:
    """Suggests which tasks to work on based on context."""

    def __init__(self, provider: AIProvider | None = None):
        """Initialize the suggester.

        Args:
            provider: AI provider to use. If None, uses config setting.
        """
        if provider is None:
            from . import get_provider
            provider = get_provider()
        self.provider = provider

    def suggest(
        self,
        tasks: list["Task"],
        hours_available: float | None = None,
        energy_level: EnergyLevel | None = None,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest tasks to work on.

        Args:
            tasks: List of all tasks
            hours_available: Available working hours
            energy_level: Current energy level (low/medium/high)
            count: Maximum number of suggestions

        Returns:
            List of SuggestionResult ordered by recommendation
        """
        return self.provider.suggest_tasks(
            tasks=tasks,
            hours_available=hours_available,
            energy_level=energy_level,
            count=count,
        )

    def suggest_quick_wins(
        self, tasks: list["Task"], max_minutes: int = 30, count: int = 5
    ) -> list[SuggestionResult]:
        """Suggest quick tasks that can be completed in limited time.

        Args:
            tasks: List of all tasks
            max_minutes: Maximum minutes per task
            count: Number of suggestions

        Returns:
            List of quick task suggestions
        """
        max_hours = max_minutes / 60

        # Filter to quick tasks
        quick_tasks = [
            t for t in tasks if t.is_open and (t.estimated_hours or 1.0) <= max_hours
        ]

        if not quick_tasks:
            return []

        return self.provider.suggest_tasks(
            tasks=quick_tasks,
            hours_available=max_hours * count,
            count=count,
        )

    def suggest_for_context(
        self,
        tasks: list["Task"],
        context: str,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest tasks based on context/mood.

        Args:
            tasks: List of all tasks
            context: Context string (e.g., "focus", "meetings", "creative")
            count: Number of suggestions

        Returns:
            List of contextual suggestions
        """
        # Map context to energy level and other filters
        context_map = {
            "focus": ("high", None),  # High energy, no time limit
            "meetings": ("medium", 1.0),  # Medium energy, short tasks
            "creative": ("high", None),  # High energy work
            "tired": ("low", None),  # Low energy
            "break": ("low", 0.5),  # Quick low-energy tasks
        }

        energy, max_hours = context_map.get(context, ("medium", None))

        return self.provider.suggest_tasks(
            tasks=tasks,
            hours_available=max_hours,
            energy_level=energy,
            count=count,
        )

    def format_suggestion(self, suggestion: SuggestionResult) -> str:
        """Format a suggestion for display.

        Args:
            suggestion: The suggestion to format

        Returns:
            Formatted string representation
        """
        task = suggestion.task
        time_str = ""
        if suggestion.estimated_minutes:
            if suggestion.estimated_minutes >= 60:
                hours = suggestion.estimated_minutes // 60
                mins = suggestion.estimated_minutes % 60
                if mins:
                    time_str = f" ({hours}h{mins}m)"
                else:
                    time_str = f" ({hours}h)"
            else:
                time_str = f" ({suggestion.estimated_minutes}m)"

        return f"{task.title}{time_str} - {suggestion.reason}"
