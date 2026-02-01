"""Rule-based AI provider (no LLM required)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from ..base import (
    AIProvider,
    AnalysisResult,
    HolisticResult,
    PlanResult,
    PortfolioInsight,
    SuggestionResult,
    TaskWithReason,
    TimeSlot,
)

if TYPE_CHECKING:
    from ...models.task import Task


class RuleBasedProvider(AIProvider):
    """Rule-based implementation using weighted scoring.

    This provider uses configurable weights to calculate priority scores
    without requiring an LLM. It serves as both a fast default and a
    fallback when LLM is unavailable.
    """

    def __init__(
        self,
        weight_deadline: float = 0.30,
        weight_dependencies: float = 0.25,
        weight_effort: float = 0.20,
        weight_staleness: float = 0.15,
        weight_priority: float = 0.10,
    ):
        """Initialize with scoring weights.

        Args:
            weight_deadline: Weight for deadline urgency (default 0.30)
            weight_dependencies: Weight for dependency impact (default 0.25)
            weight_effort: Weight for effort/complexity (default 0.20)
            weight_staleness: Weight for how long task has been open (default 0.15)
            weight_priority: Weight for explicit priority setting (default 0.10)
        """
        self.weight_deadline = weight_deadline
        self.weight_dependencies = weight_dependencies
        self.weight_effort = weight_effort
        self.weight_staleness = weight_staleness
        self.weight_priority = weight_priority

    def analyze_task(self, task: "Task", all_tasks: list["Task"]) -> AnalysisResult:
        """Analyze a task using weighted scoring rules."""
        scores = {}
        reasons = []

        # 1. Deadline score (0-100)
        deadline_score = self._calculate_deadline_score(task)
        scores["deadline"] = deadline_score
        if deadline_score >= 80:
            if task.due_date:
                days = (task.due_date - datetime.now()).days
                reasons.append(f"期限が近い（{days}日後）" if days >= 0 else "期限超過")

        # 2. Dependency score (0-100)
        dependency_score = self._calculate_dependency_score(task, all_tasks)
        scores["dependencies"] = dependency_score
        if dependency_score >= 50:
            blocked_count = len(self._get_blocked_tasks(task.id, all_tasks))
            if blocked_count > 0:
                reasons.append(f"{blocked_count}個のタスクがブロックされています")

        # 3. Effort score (0-100) - favor smaller tasks when near deadline
        effort_score = self._calculate_effort_score(task)
        scores["effort"] = effort_score

        # 4. Staleness score (0-100)
        staleness_score = self._calculate_staleness_score(task)
        scores["staleness"] = staleness_score
        if staleness_score >= 70:
            days = (datetime.now() - task.created_at).days
            reasons.append(f"{days}日間未着手")

        # 5. Priority score (0-100)
        priority_score = self._calculate_priority_score(task)
        scores["priority"] = priority_score

        # Calculate weighted total
        total_score = (
            scores["deadline"] * self.weight_deadline
            + scores["dependencies"] * self.weight_dependencies
            + scores["effort"] * self.weight_effort
            + scores["staleness"] * self.weight_staleness
            + scores["priority"] * self.weight_priority
        )

        # Generate suggestions
        suggestions = self._generate_suggestions(task, scores, all_tasks)

        # Build reasoning
        if not reasons:
            reasons.append("標準的な優先度")
        reasoning = "、".join(reasons)

        return AnalysisResult(
            task_id=task.id,
            score=round(total_score, 1),
            reasoning=reasoning,
            suggestions=suggestions,
        )

    def suggest_tasks(
        self,
        tasks: list["Task"],
        hours_available: float | None = None,
        energy_level: str | None = None,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest tasks based on analysis and constraints."""
        # Filter to open tasks only
        open_tasks = [t for t in tasks if t.is_open]

        if not open_tasks:
            return []

        # Analyze all tasks
        analyses = {t.id: self.analyze_task(t, tasks) for t in open_tasks}

        # Sort by score
        sorted_tasks = sorted(open_tasks, key=lambda t: analyses[t.id].score, reverse=True)

        # Apply energy filter if specified
        if energy_level:
            sorted_tasks = self._filter_by_energy(sorted_tasks, energy_level)

        # Apply time filter if specified
        if hours_available is not None:
            sorted_tasks = self._filter_by_time(sorted_tasks, hours_available)

        # Build suggestions
        suggestions = []
        for task in sorted_tasks[:count]:
            analysis = analyses[task.id]
            estimated_minutes = None
            if task.estimated_hours:
                estimated_minutes = int(task.estimated_hours * 60)

            suggestions.append(
                SuggestionResult(
                    task=task,
                    score=analysis.score,
                    reason=analysis.reasoning,
                    estimated_minutes=estimated_minutes,
                )
            )

        return suggestions

    def create_daily_plan(
        self,
        tasks: list["Task"],
        working_hours: float = 8.0,
        start_time: str = "09:00",
        morning_hours: float = 4.0,
        buffer_ratio: float = 0.1,
    ) -> PlanResult:
        """Create a daily plan by scheduling high-priority tasks."""
        # Get suggestions (all open tasks)
        suggestions = self.suggest_tasks(tasks, hours_available=working_hours, count=20)

        if not suggestions:
            return PlanResult(
                date=datetime.now(),
                total_hours=working_hours,
                scheduled_hours=0,
                buffer_hours=working_hours * buffer_ratio,
                warnings=["スケジュール可能なタスクがありません"],
            )

        # Calculate available time
        buffer_hours = working_hours * buffer_ratio
        available_hours = working_hours - buffer_hours

        morning_slots: list[TimeSlot] = []
        afternoon_slots: list[TimeSlot] = []
        warnings: list[str] = []
        scheduled_hours = 0.0

        # Parse start time
        start_hour, start_minute = map(int, start_time.split(":"))
        current_time = datetime.now().replace(
            hour=start_hour, minute=start_minute, second=0, microsecond=0
        )
        lunch_time = current_time + timedelta(hours=morning_hours)
        afternoon_start = lunch_time + timedelta(hours=1)  # 1 hour lunch
        end_time = current_time + timedelta(hours=working_hours + 1)  # +1 for lunch

        # Check for overdue tasks
        for suggestion in suggestions:
            if suggestion.task.due_date and suggestion.task.due_date < datetime.now():
                warnings.append(f"「{suggestion.task.title}」は期限超過です")
            elif suggestion.task.due_date and suggestion.task.due_date < datetime.now() + timedelta(
                days=1
            ):
                warnings.append(f"「{suggestion.task.title}」は明日が期限です")

        # Schedule tasks
        is_morning = True
        slot_start = current_time

        for suggestion in suggestions:
            if scheduled_hours >= available_hours:
                break

            # Estimate duration
            duration_hours = suggestion.task.estimated_hours or 1.0

            # Check if fits in remaining time
            if scheduled_hours + duration_hours > available_hours:
                # Try to fit partially or skip
                remaining = available_hours - scheduled_hours
                if remaining >= 0.5:  # At least 30 min
                    duration_hours = remaining
                else:
                    continue

            # Create time slot
            slot_end = slot_start + timedelta(hours=duration_hours)

            # Check if we need to switch to afternoon
            if is_morning and slot_end > lunch_time:
                if slot_start < lunch_time:
                    # Adjust duration to fit in morning
                    morning_remaining = (lunch_time - slot_start).seconds / 3600
                    if morning_remaining >= 0.5:
                        duration_hours = morning_remaining
                        slot_end = lunch_time
                    else:
                        # Move to afternoon
                        is_morning = False
                        slot_start = afternoon_start
                        slot_end = slot_start + timedelta(hours=duration_hours)
                else:
                    is_morning = False
                    slot_start = afternoon_start
                    slot_end = slot_start + timedelta(hours=duration_hours)

            # Don't schedule past end time
            if slot_end > end_time:
                break

            time_slot = TimeSlot(
                start_time=slot_start.strftime("%H:%M"),
                end_time=slot_end.strftime("%H:%M"),
                task=suggestion.task,
                duration_hours=duration_hours,
            )

            if is_morning:
                morning_slots.append(time_slot)
            else:
                afternoon_slots.append(time_slot)

            scheduled_hours += duration_hours
            slot_start = slot_end

            # Switch to afternoon after lunch
            if is_morning and slot_start >= lunch_time:
                is_morning = False
                slot_start = afternoon_start

        return PlanResult(
            date=datetime.now(),
            total_hours=working_hours,
            scheduled_hours=round(scheduled_hours, 1),
            buffer_hours=round(buffer_hours, 1),
            morning_slots=morning_slots,
            afternoon_slots=afternoon_slots,
            warnings=warnings,
        )

    # Helper methods

    def _calculate_deadline_score(self, task: "Task") -> float:
        """Calculate urgency score based on deadline."""
        if not task.due_date:
            return 30.0  # No deadline = moderate baseline

        days_until = (task.due_date - datetime.now()).days

        if days_until < 0:
            return 100.0  # Overdue
        elif days_until == 0:
            return 95.0  # Due today
        elif days_until == 1:
            return 90.0  # Due tomorrow
        elif days_until <= 3:
            return 80.0  # Due within 3 days
        elif days_until <= 7:
            return 60.0  # Due within a week
        elif days_until <= 14:
            return 40.0  # Due within 2 weeks
        elif days_until <= 30:
            return 20.0  # Due within a month
        else:
            return 10.0  # Far future

    def _calculate_dependency_score(self, task: "Task", all_tasks: list["Task"]) -> float:
        """Calculate impact score based on how many tasks this blocks."""
        blocked_tasks = self._get_blocked_tasks(task.id, all_tasks)
        blocked_count = len(blocked_tasks)

        if blocked_count == 0:
            return 20.0
        elif blocked_count == 1:
            return 50.0
        elif blocked_count == 2:
            return 70.0
        elif blocked_count <= 4:
            return 85.0
        else:
            return 100.0

    def _get_blocked_tasks(self, task_id: str, all_tasks: list["Task"]) -> list["Task"]:
        """Get tasks that are blocked by the given task."""
        return [t for t in all_tasks if task_id in t.dependencies and t.is_open]

    def _calculate_effort_score(self, task: "Task") -> float:
        """Calculate effort score (higher for smaller tasks)."""
        if not task.estimated_hours:
            return 50.0  # Unknown effort

        hours = task.estimated_hours
        if hours <= 0.5:
            return 90.0  # Quick win
        elif hours <= 1:
            return 80.0
        elif hours <= 2:
            return 60.0
        elif hours <= 4:
            return 40.0
        elif hours <= 8:
            return 20.0
        else:
            return 10.0  # Large task

    def _calculate_staleness_score(self, task: "Task") -> float:
        """Calculate staleness based on how long task has been open."""
        days_open = (datetime.now() - task.created_at).days

        if days_open <= 1:
            return 10.0  # Fresh
        elif days_open <= 3:
            return 30.0
        elif days_open <= 7:
            return 50.0
        elif days_open <= 14:
            return 70.0
        elif days_open <= 30:
            return 85.0
        else:
            return 100.0  # Very stale

    def _calculate_priority_score(self, task: "Task") -> float:
        """Convert explicit priority to score."""
        from ...models.enums import Priority

        priority_map = {
            Priority.URGENT: 100.0,
            Priority.HIGH: 80.0,
            Priority.MEDIUM: 50.0,
            Priority.LOW: 30.0,
            Priority.LOWEST: 10.0,
        }
        return priority_map.get(task.priority, 50.0)

    def _generate_suggestions(
        self, task: "Task", scores: dict[str, float], all_tasks: list["Task"]
    ) -> list[str]:
        """Generate actionable suggestions based on analysis."""
        suggestions = []

        # Check blocking dependencies
        blocking = [t for t in all_tasks if t.id in task.dependencies and t.is_open]
        if blocking:
            suggestions.append(f"まず「{blocking[0].title}」を完了してください（依存関係）")

        # Check if task is stale
        if scores["staleness"] >= 70:
            suggestions.append("長期間未着手です。分割を検討してください")

        # Check if effort is high
        if scores["effort"] <= 20:
            suggestions.append("大きなタスクです。サブタスクに分割を検討してください")

        # Check deadline urgency
        if scores["deadline"] >= 90 and task.status.value == "pending":
            suggestions.append("すぐに着手してください")

        return suggestions

    def _filter_by_energy(self, tasks: list["Task"], energy_level: str) -> list["Task"]:
        """Filter tasks by energy level requirement."""
        if energy_level == "low":
            # Prefer smaller tasks and routine work
            return sorted(tasks, key=lambda t: t.estimated_hours or 1.0)
        elif energy_level == "high":
            # Can handle complex tasks
            return tasks  # No filter, use priority order
        else:  # medium
            # Filter out very large tasks
            return [t for t in tasks if (t.estimated_hours or 1.0) <= 4.0]

    def _filter_by_time(self, tasks: list["Task"], hours_available: float) -> list["Task"]:
        """Filter tasks that can fit in available time."""
        result = []
        total_hours = 0.0

        for task in tasks:
            task_hours = task.estimated_hours or 1.0
            if total_hours + task_hours <= hours_available:
                result.append(task)
                total_hours += task_hours
            elif task_hours <= hours_available:
                # Task fits by itself, include it
                result.append(task)

        return result

    def analyze_portfolio(
        self,
        tasks: list["Task"],
        max_tasks: int = 20,
    ) -> HolisticResult:
        """Analyze all tasks holistically using rule-based heuristics.

        Args:
            tasks: List of open tasks to analyze
            max_tasks: Maximum number of tasks to include

        Returns:
            HolisticResult with portfolio-level insights
        """
        if not tasks:
            return HolisticResult(
                overall_assessment="分析対象のタスクがありません。",
                total_tasks=0,
                analyzed_tasks=0,
            )

        # Take top tasks by priority
        analyzed_tasks = tasks[:max_tasks]
        total_tasks = len(tasks)

        # Analyze each task
        analyses = {t.id: self.analyze_task(t, tasks) for t in analyzed_tasks}

        # Sort by score to get recommended order
        sorted_tasks = sorted(
            analyzed_tasks, key=lambda t: analyses[t.id].score, reverse=True
        )
        recommended_order = [t.id for t in sorted_tasks]

        # Build ranked tasks with reasons
        ranked_tasks = [
            TaskWithReason(
                task_id=t.id,
                score=analyses[t.id].score,
                reason=analyses[t.id].reasoning,
            )
            for t in sorted_tasks
        ]

        # Build insights
        insights: list[PortfolioInsight] = []
        warnings: list[str] = []

        # 1. Check for overdue tasks
        overdue_tasks = [t for t in analyzed_tasks if t.due_date and t.due_date < datetime.now()]
        if overdue_tasks:
            insights.append(
                PortfolioInsight(
                    insight_type="warning",
                    related_tasks=[t.id for t in overdue_tasks],
                    description=f"{len(overdue_tasks)}件のタスクが期限超過しています",
                    priority=1,
                )
            )
            warnings.append(f"{len(overdue_tasks)}件のタスクが期限超過")

        # 2. Check for tasks due soon (within 3 days)
        soon_tasks = [
            t
            for t in analyzed_tasks
            if t.due_date
            and datetime.now() <= t.due_date < datetime.now() + timedelta(days=3)
        ]
        if soon_tasks:
            insights.append(
                PortfolioInsight(
                    insight_type="sequence",
                    related_tasks=[t.id for t in soon_tasks],
                    description=f"{len(soon_tasks)}件のタスクが3日以内に期限を迎えます",
                    priority=2,
                )
            )

        # 3. Find blocking tasks (tasks that block others)
        blocker_tasks = []
        for t in analyzed_tasks:
            blocked_by_this = self._get_blocked_tasks(t.id, tasks)
            if len(blocked_by_this) >= 2:
                blocker_tasks.append((t, len(blocked_by_this)))
        if blocker_tasks:
            blocker_tasks.sort(key=lambda x: x[1], reverse=True)
            top_blocker = blocker_tasks[0]
            insights.append(
                PortfolioInsight(
                    insight_type="blocker",
                    related_tasks=[top_blocker[0].id],
                    description=f"「{top_blocker[0].title}」が{top_blocker[1]}件のタスクをブロックしています",
                    priority=1,
                )
            )

        # 4. Group by priority
        from ...models.enums import Priority

        priority_groups: dict[str, list[str]] = {}
        for t in analyzed_tasks:
            key = t.priority.value
            if key not in priority_groups:
                priority_groups[key] = []
            priority_groups[key].append(t.id)

        task_groups: list[tuple[str, list[str]]] = []
        for priority, task_ids in priority_groups.items():
            if len(task_ids) >= 2:
                task_groups.append((f"優先度: {priority}", task_ids))

        # 5. Check for stale tasks
        stale_tasks = [
            t for t in analyzed_tasks if (datetime.now() - t.created_at).days >= 14
        ]
        if stale_tasks:
            insights.append(
                PortfolioInsight(
                    insight_type="optimization",
                    related_tasks=[t.id for t in stale_tasks],
                    description=f"{len(stale_tasks)}件のタスクが2週間以上未着手です",
                    priority=3,
                )
            )

        # Build overall assessment
        high_priority_count = len([t for t in analyzed_tasks if analyses[t.id].score >= 70])
        assessment_parts = [f"{len(analyzed_tasks)}件のタスクを分析しました。"]
        if high_priority_count > 0:
            assessment_parts.append(f"高優先度: {high_priority_count}件。")
        if overdue_tasks:
            assessment_parts.append(f"期限超過: {len(overdue_tasks)}件に注意。")

        result = HolisticResult(
            insights=insights,
            ranked_tasks=ranked_tasks,
            recommended_order=recommended_order,
            task_groups=task_groups,
            overall_assessment=" ".join(assessment_parts),
            warnings=warnings,
            total_tasks=total_tasks,
            analyzed_tasks=len(analyzed_tasks),
        )

        # Add warning if tasks were truncated
        if total_tasks > max_tasks:
            result.warnings.insert(
                0, f"タスク数が多いため、上位{max_tasks}件のみ分析しました（全{total_tasks}件中）"
            )

        return result
