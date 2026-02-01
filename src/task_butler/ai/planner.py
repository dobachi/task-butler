"""Daily planning assistant."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from .base import AIProvider, PlanResult

if TYPE_CHECKING:
    from ..models.task import Task


class DailyPlanner:
    """Creates daily work plans based on tasks and preferences."""

    def __init__(
        self,
        provider: AIProvider | None = None,
        default_hours: float = 8.0,
        buffer_ratio: float = 0.1,
        morning_hours: float = 4.0,
        start_time: str = "09:00",
    ):
        """Initialize the planner.

        Args:
            provider: AI provider to use. If None, uses config setting.
            default_hours: Default working hours per day
            buffer_ratio: Ratio of time to reserve as buffer
            morning_hours: Hours before lunch break
            start_time: Default start time (HH:MM)
        """
        if provider is None:
            from . import get_provider
            provider = get_provider()
        self.provider = provider
        self.default_hours = default_hours
        self.buffer_ratio = buffer_ratio
        self.morning_hours = morning_hours
        self.start_time = start_time

    def create_plan(
        self,
        tasks: list["Task"],
        working_hours: float | None = None,
        target_date: datetime | None = None,
    ) -> PlanResult:
        """Create a daily work plan.

        Args:
            tasks: List of all tasks
            working_hours: Working hours for the day
            target_date: Date to plan for (defaults to today)

        Returns:
            PlanResult with scheduled time slots
        """
        hours = working_hours or self.default_hours

        result = self.provider.create_daily_plan(
            tasks=tasks,
            working_hours=hours,
            start_time=self.start_time,
            morning_hours=self.morning_hours,
            buffer_ratio=self.buffer_ratio,
        )

        # Override date if specified
        if target_date:
            result.date = target_date

        return result

    def format_plan(self, plan: PlanResult) -> str:
        """Format a plan for display.

        Args:
            plan: The plan to format

        Returns:
            Formatted string representation
        """
        lines = []

        # Header
        date_str = plan.date.strftime("%Y-%m-%d")
        lines.append(f"📅 {date_str} の作業計画（{plan.total_hours}時間）")
        lines.append("")

        # Morning slots
        if plan.morning_slots:
            morning_hours = sum(s.duration_hours for s in plan.morning_slots)
            lines.append(f"午前（{morning_hours:.1f}時間）:")
            for slot in plan.morning_slots:
                priority_icon = self._get_priority_icon(slot.task.priority)
                lines.append(
                    f"  {slot.start_time}-{slot.end_time} "
                    f"{priority_icon} {slot.task.title} ({slot.duration_hours}h)"
                )
            lines.append("")

        # Afternoon slots
        if plan.afternoon_slots:
            afternoon_hours = sum(s.duration_hours for s in plan.afternoon_slots)
            lines.append(f"午後（{afternoon_hours:.1f}時間）:")
            for slot in plan.afternoon_slots:
                priority_icon = self._get_priority_icon(slot.task.priority)
                lines.append(
                    f"  {slot.start_time}-{slot.end_time} "
                    f"{priority_icon} {slot.task.title} ({slot.duration_hours}h)"
                )
            lines.append("")

        # Buffer
        if plan.buffer_hours > 0:
            lines.append(f"バッファ/予備時間: {plan.buffer_hours:.1f}時間")
            lines.append("")

        # Warnings
        if plan.warnings:
            for warning in plan.warnings:
                lines.append(f"⚠️ {warning}")

        # Summary
        lines.append("")
        lines.append(
            f"スケジュール済み: {plan.scheduled_hours:.1f}h / {plan.total_hours}h"
        )

        return "\n".join(lines)

    def _get_priority_icon(self, priority) -> str:
        """Get icon for priority level."""
        from ..models.enums import Priority

        icons = {
            Priority.URGENT: "[urgent]",
            Priority.HIGH: "[high]",
            Priority.MEDIUM: "[medium]",
            Priority.LOW: "[low]",
            Priority.LOWEST: "[lowest]",
        }
        return icons.get(priority, "[medium]")
