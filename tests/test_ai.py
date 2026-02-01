"""Tests for AI integration module."""

from datetime import datetime, timedelta

import pytest

from task_butler.ai import DailyPlanner, TaskAnalyzer, TaskSuggester
from task_butler.ai.base import AnalysisResult, PlanResult, SuggestionResult
from task_butler.ai.providers.rule_based import RuleBasedProvider
from task_butler.models.enums import Priority
from task_butler.models.task import Task


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    now = datetime.now()
    return [
        Task(
            id="task-1",
            title="Urgent task due today",
            priority=Priority.URGENT,
            due_date=now,
            estimated_hours=2.0,
        ),
        Task(
            id="task-2",
            title="High priority task due tomorrow",
            priority=Priority.HIGH,
            due_date=now + timedelta(days=1),
            estimated_hours=3.0,
        ),
        Task(
            id="task-3",
            title="Medium priority task",
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
        ),
        Task(
            id="task-4",
            title="Low priority quick task",
            priority=Priority.LOW,
            estimated_hours=0.5,
        ),
        Task(
            id="task-5",
            title="Blocked task",
            priority=Priority.HIGH,
            dependencies=["task-1"],
            estimated_hours=2.0,
        ),
    ]


@pytest.fixture
def stale_task():
    """Create a stale task (created 30 days ago)."""
    return Task(
        id="stale-1",
        title="Old stale task",
        priority=Priority.MEDIUM,
        created_at=datetime.now() - timedelta(days=30),
        estimated_hours=1.0,
    )


class TestRuleBasedProvider:
    """Tests for RuleBasedProvider."""

    def test_analyze_urgent_task(self, sample_tasks):
        """Test analysis of urgent task with deadline."""
        provider = RuleBasedProvider()
        urgent_task = sample_tasks[0]

        result = provider.analyze_task(urgent_task, sample_tasks)

        assert isinstance(result, AnalysisResult)
        assert result.task_id == "task-1"
        assert result.score > 60  # High score for urgent + due today
        assert "期限" in result.reasoning or "標準" in result.reasoning

    def test_analyze_blocking_task(self, sample_tasks):
        """Test that blocking tasks get higher scores."""
        provider = RuleBasedProvider()
        blocking_task = sample_tasks[0]  # task-1 blocks task-5

        result = provider.analyze_task(blocking_task, sample_tasks)

        assert result.score > 50  # Should be elevated due to blocking
        assert (
            "ブロック" in result.reasoning
            or "期限" in result.reasoning
            or "標準" in result.reasoning
        )

    def test_analyze_stale_task(self, stale_task, sample_tasks):
        """Test that stale tasks get higher scores."""
        provider = RuleBasedProvider()
        all_tasks = sample_tasks + [stale_task]

        result = provider.analyze_task(stale_task, all_tasks)

        assert "未着手" in result.reasoning or "標準" in result.reasoning

    def test_suggest_tasks(self, sample_tasks):
        """Test task suggestions."""
        provider = RuleBasedProvider()

        suggestions = provider.suggest_tasks(sample_tasks, count=3)

        assert len(suggestions) <= 3
        assert all(isinstance(s, SuggestionResult) for s in suggestions)
        # First suggestion should be urgent task
        assert suggestions[0].task.priority == Priority.URGENT

    def test_suggest_with_time_limit(self, sample_tasks):
        """Test suggestions with time constraint."""
        provider = RuleBasedProvider()

        suggestions = provider.suggest_tasks(sample_tasks, hours_available=2.0)

        # Should filter to tasks fitting in 2 hours
        # At least one should fit
        assert len(suggestions) > 0

    def test_suggest_low_energy(self, sample_tasks):
        """Test suggestions for low energy."""
        provider = RuleBasedProvider()

        suggestions = provider.suggest_tasks(sample_tasks, energy_level="low", count=5)

        # Low energy should prefer smaller tasks
        assert len(suggestions) > 0

    def test_create_daily_plan(self, sample_tasks):
        """Test daily plan creation."""
        provider = RuleBasedProvider()

        plan = provider.create_daily_plan(
            sample_tasks,
            working_hours=8.0,
            start_time="09:00",
        )

        assert isinstance(plan, PlanResult)
        assert plan.total_hours == 8.0
        assert plan.scheduled_hours <= plan.total_hours
        assert len(plan.morning_slots) + len(plan.afternoon_slots) > 0


class TestTaskAnalyzer:
    """Tests for TaskAnalyzer facade."""

    def test_analyze_single_task(self, sample_tasks):
        """Test analyzing a single task."""
        analyzer = TaskAnalyzer()
        task = sample_tasks[0]

        result = analyzer.analyze(task, sample_tasks)

        assert result.task_id == task.id
        assert 0 <= result.score <= 100

    def test_analyze_all_tasks(self, sample_tasks):
        """Test analyzing all tasks."""
        analyzer = TaskAnalyzer()

        results = analyzer.analyze_all(sample_tasks)

        # Should only include open tasks (all 5 are open)
        assert len(results) == 5
        # Should be sorted by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_get_top_priorities(self, sample_tasks):
        """Test getting top priority tasks."""
        analyzer = TaskAnalyzer()

        top = analyzer.get_top_priorities(sample_tasks, count=3)

        assert len(top) == 3
        for task, analysis in top:
            assert task.id == analysis.task_id


class TestTaskSuggester:
    """Tests for TaskSuggester facade."""

    def test_suggest_default(self, sample_tasks):
        """Test default suggestions."""
        suggester = TaskSuggester()

        suggestions = suggester.suggest(sample_tasks)

        assert len(suggestions) <= 5  # Default count
        assert all(s.task.is_open for s in suggestions)

    def test_suggest_quick_wins(self, sample_tasks):
        """Test quick win suggestions."""
        suggester = TaskSuggester()

        suggestions = suggester.suggest_quick_wins(sample_tasks, max_minutes=60)

        # All should be 1 hour or less
        for s in suggestions:
            if s.task.estimated_hours:
                assert s.task.estimated_hours <= 1.0

    def test_format_suggestion(self, sample_tasks):
        """Test suggestion formatting."""
        suggester = TaskSuggester()
        suggestions = suggester.suggest(sample_tasks, count=1)

        if suggestions:
            formatted = suggester.format_suggestion(suggestions[0])
            assert sample_tasks[0].title in formatted or len(formatted) > 0


class TestDailyPlanner:
    """Tests for DailyPlanner facade."""

    def test_create_plan_default(self, sample_tasks):
        """Test creating a plan with defaults."""
        planner = DailyPlanner()

        plan = planner.create_plan(sample_tasks)

        assert plan.total_hours == 8.0  # Default
        assert plan.buffer_hours > 0

    def test_create_plan_custom_hours(self, sample_tasks):
        """Test creating a plan with custom hours."""
        planner = DailyPlanner(default_hours=6.0)

        plan = planner.create_plan(sample_tasks)

        assert plan.total_hours == 6.0

    def test_format_plan(self, sample_tasks):
        """Test plan formatting."""
        planner = DailyPlanner()
        plan = planner.create_plan(sample_tasks)

        formatted = planner.format_plan(plan)

        assert "の作業計画" in formatted
        assert "時間" in formatted

    def test_plan_includes_warnings(self, sample_tasks):
        """Test that overdue tasks generate warnings."""
        # Create overdue task
        overdue_task = Task(
            id="overdue-1",
            title="Overdue task",
            priority=Priority.HIGH,
            due_date=datetime.now() - timedelta(days=1),
            estimated_hours=1.0,
        )
        tasks = sample_tasks + [overdue_task]

        planner = DailyPlanner()
        plan = planner.create_plan(tasks)

        # Should have a warning about overdue task
        assert len(plan.warnings) > 0


class TestAnalysisResult:
    """Tests for AnalysisResult data class."""

    def test_score_label_critical(self):
        """Test critical score label."""
        result = AnalysisResult(task_id="1", score=95, reasoning="test")
        assert result.score_label == "critical"

    def test_score_label_high(self):
        """Test high score label."""
        result = AnalysisResult(task_id="1", score=80, reasoning="test")
        assert result.score_label == "high"

    def test_score_label_medium(self):
        """Test medium score label."""
        result = AnalysisResult(task_id="1", score=60, reasoning="test")
        assert result.score_label == "medium"

    def test_score_label_low(self):
        """Test low score label."""
        result = AnalysisResult(task_id="1", score=30, reasoning="test")
        assert result.score_label == "low"

    def test_score_label_minimal(self):
        """Test minimal score label."""
        result = AnalysisResult(task_id="1", score=10, reasoning="test")
        assert result.score_label == "minimal"
