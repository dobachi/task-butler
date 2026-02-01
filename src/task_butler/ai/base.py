"""Base classes and data models for AI integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.task import Task


@dataclass
class AnalysisResult:
    """Result of analyzing a single task."""

    task_id: str
    score: float  # 0-100 priority score
    reasoning: str  # Explanation of the score
    suggestions: list[str] = field(default_factory=list)  # Action suggestions

    @property
    def score_label(self) -> str:
        """Return a human-readable score label."""
        if self.score >= 90:
            return "critical"
        elif self.score >= 75:
            return "high"
        elif self.score >= 50:
            return "medium"
        elif self.score >= 25:
            return "low"
        else:
            return "minimal"


@dataclass
class SuggestionResult:
    """A suggested task to work on."""

    task: "Task"
    score: float  # 0-100 recommendation score
    reason: str  # Why this task is suggested
    estimated_minutes: int | None = None  # Estimated time to complete


@dataclass
class TimeSlot:
    """A time slot in a daily plan."""

    start_time: str  # HH:MM format
    end_time: str  # HH:MM format
    task: "Task"
    duration_hours: float


@dataclass
class PlanResult:
    """Result of daily planning."""

    date: datetime
    total_hours: float
    scheduled_hours: float
    buffer_hours: float
    morning_slots: list[TimeSlot] = field(default_factory=list)
    afternoon_slots: list[TimeSlot] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # e.g., overdue tasks


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    def analyze_task(self, task: "Task", all_tasks: list["Task"]) -> AnalysisResult:
        """Analyze a single task and return priority score with reasoning.

        Args:
            task: The task to analyze
            all_tasks: All tasks for context (dependencies, etc.)

        Returns:
            AnalysisResult with score and reasoning
        """
        pass

    @abstractmethod
    def suggest_tasks(
        self,
        tasks: list["Task"],
        hours_available: float | None = None,
        energy_level: str | None = None,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest which tasks to work on next.

        Args:
            tasks: List of open tasks to consider
            hours_available: Available working hours (optional)
            energy_level: Current energy level (low/medium/high)
            count: Maximum number of suggestions

        Returns:
            List of SuggestionResult ordered by recommendation
        """
        pass

    @abstractmethod
    def create_daily_plan(
        self,
        tasks: list["Task"],
        working_hours: float = 8.0,
        start_time: str = "09:00",
        morning_hours: float = 4.0,
        buffer_ratio: float = 0.1,
    ) -> PlanResult:
        """Create a daily work plan.

        Args:
            tasks: List of open tasks to schedule
            working_hours: Total working hours for the day
            start_time: Start time in HH:MM format
            morning_hours: Hours before lunch break
            buffer_ratio: Ratio of time to reserve as buffer

        Returns:
            PlanResult with scheduled time slots
        """
        pass
