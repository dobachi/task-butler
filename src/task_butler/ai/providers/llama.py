"""LLM-based AI provider using llama-cpp-python."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..base import (
    AIProvider,
    AnalysisResult,
    HolisticResult,
    PlanResult,
    PortfolioInsight,
    SuggestionResult,
    TaskWithReason,
)
from ..model_manager import DEFAULT_MODEL, ModelManager
from ..prompts import PromptManager
from .rule_based import RuleBasedProvider

if TYPE_CHECKING:
    from ...models.task import Task

# Check if llama-cpp-python is available
try:
    from llama_cpp import Llama

    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    Llama = None


class LlamaProvider(AIProvider):
    """AI provider using local LLM via llama-cpp-python.

    Falls back to RuleBasedProvider if LLM is unavailable.
    """

    # Model families and their prompt formats
    LLAMA2_MODELS = ["elyza", "llama-2", "japanese-llama"]  # Use [INST] format
    CHATML_MODELS = ["tinyllama", "phi"]  # Use <|system|> format

    def __init__(
        self,
        model_path: str | None = None,
        model_name: str = DEFAULT_MODEL,
        n_ctx: int = 2048,
        n_gpu_layers: int = 0,
        verbose: bool = False,
        language: str = "ja",
    ):
        """Initialize Llama provider.

        Args:
            model_path: Path to GGUF model file. If None, uses model_name.
            model_name: Name of model to use if model_path not specified.
            n_ctx: Context window size.
            n_gpu_layers: Number of layers to offload to GPU.
            verbose: Whether to show verbose output.
            language: Output language ('en' for English, 'ja' for Japanese).
        """
        self.model_path = model_path
        self.model_name = model_name
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        self.language = language if language in ("en", "ja") else "ja"
        self._llm = None
        self._fallback = RuleBasedProvider()
        self._model_manager = ModelManager()
        self._prompt_manager = PromptManager(self.language)

    def _is_llama2_model(self) -> bool:
        """Check if current model uses Llama-2 prompt format."""
        model_lower = self.model_name.lower()
        return any(family in model_lower for family in self.LLAMA2_MODELS)

    def _format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Format prompt based on model type."""
        if self._is_llama2_model():
            # Llama-2 / ELYZA format
            return f"""[INST] <<SYS>>
{system_prompt}
<</SYS>>

{user_prompt} [/INST]"""
        else:
            # ChatML format (TinyLlama, Phi, etc.)
            return f"""<|system|>
{system_prompt}
</s>
<|user|>
{user_prompt}
</s>
<|assistant|>
"""

    def _get_llm(self):
        """Get or initialize the LLM instance."""
        if self._llm is not None:
            return self._llm

        if not LLAMA_AVAILABLE:
            return None

        # Determine model path
        if self.model_path:
            from pathlib import Path

            path = Path(self.model_path)
            if not path.exists():
                return None
        else:
            path = self._model_manager.get_model_path(self.model_name)
            if path is None:
                # Model not downloaded, use fallback
                return None

        try:
            from rich.console import Console
            from rich.status import Status

            console = Console()
            with Status(
                f"[dim]モデルをロード中: {self.model_name}...[/dim]",
                console=console,
                spinner="dots",
            ):
                self._llm = Llama(
                    model_path=str(path),
                    n_ctx=self.n_ctx,
                    n_gpu_layers=self.n_gpu_layers,
                    verbose=self.verbose,
                )
            return self._llm
        except Exception:
            return None

    def _generate(self, prompt: str, max_tokens: int = 512) -> str | None:
        """Generate text from prompt.

        Args:
            prompt: The prompt to generate from.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text or None if generation failed.
        """
        llm = self._get_llm()
        if llm is None:
            return None

        try:
            from rich.console import Console
            from rich.status import Status

            console = Console()
            with Status(
                "[dim]AI分析中...[/dim]",
                console=console,
                spinner="dots",
            ):
                result = llm(
                    prompt,
                    max_tokens=max_tokens,
                    stop=["</s>", "\n\n\n"],
                    echo=False,
                )
            return result["choices"][0]["text"].strip()
        except Exception:
            return None

    def analyze_task(self, task: "Task", all_tasks: list["Task"]) -> AnalysisResult:
        """Analyze a task using LLM for reasoning, rules for scoring."""
        # Get rule-based analysis for reliable scoring
        rule_result = self._fallback.analyze_task(task, all_tasks)

        # Try LLM enhancement for natural language reasoning
        llm = self._get_llm()
        if llm is None:
            # Mark as fallback
            return AnalysisResult(
                task_id=rule_result.task_id,
                score=rule_result.score,
                reasoning=f"📋 {rule_result.reasoning}",
                suggestions=rule_result.suggestions,
            )

        # Build context about the task
        context = self._build_task_context(task, all_tasks)

        # Get prompts from manager
        system_prompt = self._prompt_manager.get("analyze_system")
        user_prompt = self._prompt_manager.format(
            "analyze_user", context=context, score=rule_result.score
        )

        prompt = self._format_prompt(system_prompt, user_prompt)

        response = self._generate(prompt, max_tokens=150)
        if response:
            # Clean up the response
            reasoning = response.strip()
            # Remove any incomplete sentences at the end
            if reasoning and not reasoning.endswith(("。", ".", "!", "?")):
                last_period = max(reasoning.rfind("。"), reasoning.rfind("."))
                if last_period > 0:
                    reasoning = reasoning[: last_period + 1]

            if reasoning and len(reasoning) > 10:
                # Generate suggestions using LLM
                suggestions = self._generate_suggestions_llm(task, context)

                return AnalysisResult(
                    task_id=task.id,
                    score=rule_result.score,
                    reasoning=f"🤖 {reasoning}",
                    suggestions=suggestions or rule_result.suggestions,
                )

        # LLM response was empty or too short, fallback to rule-based
        return AnalysisResult(
            task_id=rule_result.task_id,
            score=rule_result.score,
            reasoning=f"📋 {rule_result.reasoning}",
            suggestions=rule_result.suggestions,
        )

    def _generate_suggestions_llm(self, task: "Task", context: str) -> list[str]:
        """Generate action suggestions using LLM."""
        system_prompt = self._prompt_manager.get("suggest_system")
        user_prompt = self._prompt_manager.format(
            "suggest_user", title=task.title, context=context
        )

        prompt = self._format_prompt(system_prompt, user_prompt)
        response = self._generate(prompt, max_tokens=100)
        if response:
            lines = [line.strip() for line in response.strip().split("\n") if line.strip()]
            # Clean up suggestions
            suggestions = []
            for line in lines[:2]:
                # Remove numbering
                line = re.sub(r"^[\d\.\-\*]+\s*", "", line)
                if line and len(line) > 5:
                    suggestions.append(line)
            return suggestions
        return []

    def suggest_tasks(
        self,
        tasks: list["Task"],
        hours_available: float | None = None,
        energy_level: str | None = None,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest tasks with LLM-generated reasons."""
        # Get rule-based suggestions for ordering
        rule_suggestions = self._fallback.suggest_tasks(tasks, hours_available, energy_level, count)

        llm = self._get_llm()
        if llm is None:
            # Mark as fallback
            return [
                SuggestionResult(
                    task=s.task,
                    score=s.score,
                    reason=f"📋 {s.reason}",
                    estimated_minutes=s.estimated_minutes,
                )
                for s in rule_suggestions
            ]

        # Enhance each suggestion with LLM reasoning
        enhanced_suggestions = []
        for suggestion in rule_suggestions[:count]:
            task = suggestion.task
            context = self._build_task_context(task, tasks)

            system_prompt = self._prompt_manager.get("reason_system")
            user_prompt = self._prompt_manager.format(
                "reason_user", title=task.title, context=context
            )

            prompt = self._format_prompt(system_prompt, user_prompt)
            response = self._generate(prompt, max_tokens=80)
            reason = f"📋 {suggestion.reason}"  # Default to rule-based with fallback marker

            if response:
                cleaned = response.strip()
                # Take first sentence only
                for sep in ["。", ".", "\n"]:
                    if sep in cleaned:
                        cleaned = cleaned.split(sep)[0] + ("。" if sep == "。" else "")
                        break
                if cleaned and len(cleaned) > 5:
                    reason = f"🤖 {cleaned}"

            enhanced_suggestions.append(
                SuggestionResult(
                    task=task,
                    score=suggestion.score,
                    reason=reason,
                    estimated_minutes=suggestion.estimated_minutes,
                )
            )

        return enhanced_suggestions

    def create_daily_plan(
        self,
        tasks: list["Task"],
        working_hours: float = 8.0,
        start_time: str = "09:00",
        morning_hours: float = 4.0,
        buffer_ratio: float = 0.1,
    ) -> PlanResult:
        """Create daily plan using LLM or fallback to rules.

        For planning, we primarily use rule-based logic for reliability,
        but can enhance with LLM insights for warnings/suggestions.
        """
        # Use rule-based for reliable scheduling
        return self._fallback.create_daily_plan(
            tasks, working_hours, start_time, morning_hours, buffer_ratio
        )

    def analyze_portfolio(
        self,
        tasks: list["Task"],
        max_tasks: int = 20,
    ) -> HolisticResult:
        """Analyze all tasks holistically using LLM.

        Args:
            tasks: List of open tasks to analyze
            max_tasks: Maximum number of tasks to include (context window limit)

        Returns:
            HolisticResult with portfolio-level insights
        """
        if not tasks:
            return HolisticResult(
                overall_assessment="分析対象のタスクがありません。"
                if self.language == "ja"
                else "No tasks to analyze.",
                total_tasks=0,
                analyzed_tasks=0,
            )

        # Sort by priority score and take top N tasks
        analyzed_tasks = tasks[:max_tasks]
        total_tasks = len(tasks)

        # Try LLM analysis
        llm = self._get_llm()
        if llm is None:
            return self._fallback.analyze_portfolio(tasks, max_tasks)

        # Build compact task summary
        task_list = self._build_portfolio_summary(analyzed_tasks)

        # Get prompts
        system_prompt = self._prompt_manager.get("portfolio_system")
        user_prompt = self._prompt_manager.format(
            "portfolio_user",
            task_count=len(analyzed_tasks),
            task_list=task_list,
        )

        prompt = self._format_prompt(system_prompt, user_prompt)
        response = self._generate(prompt, max_tokens=1200)

        if response:
            result = self._parse_portfolio_response(response, analyzed_tasks)
            result.total_tasks = total_tasks
            result.analyzed_tasks = len(analyzed_tasks)

            # Get rule-based scores for reliable scoring
            analyses = {t.id: self._fallback.analyze_task(t, tasks) for t in analyzed_tasks}

            # Get LLM reasons (stored in _parse_portfolio_response)
            llm_reasons = getattr(result, "_llm_reasons", {})

            # Build ranked_tasks with LLM reasons (fallback to rule-based if no LLM reason)
            result.ranked_tasks = [
                TaskWithReason(
                    task_id=tid,
                    score=analyses[tid].score if tid in analyses else 50.0,
                    reason=llm_reasons.get(tid) or (
                        analyses[tid].reasoning if tid in analyses else "分析データなし"
                    ),
                )
                for tid in result.recommended_order
            ]

            # Add warning if tasks were truncated
            if total_tasks > max_tasks:
                warning = (
                    f"タスク数が多いため、上位{max_tasks}件のみ分析しました（全{total_tasks}件中）"
                    if self.language == "ja"
                    else f"Analyzed top {max_tasks} tasks out of {total_tasks} due to context limit"
                )
                result.warnings.insert(0, warning)

            return result

        # Fallback if LLM fails
        return self._fallback.analyze_portfolio(tasks, max_tasks)

    def _build_portfolio_summary(self, tasks: list["Task"]) -> str:
        """Build a compact summary of all tasks for portfolio analysis."""
        from datetime import datetime

        lines = []
        for t in tasks:
            parts = [f"[{t.short_id}] {t.title}"]

            # Priority
            parts.append(f"({t.priority.value})")

            # Deadline
            if t.due_date:
                days = (t.due_date - datetime.now()).days
                if days < 0:
                    parts.append(f"期限{-days}日超過" if self.language == "ja" else f"{-days}d overdue")
                elif days == 0:
                    parts.append("今日期限" if self.language == "ja" else "due today")
                elif days <= 7:
                    parts.append(f"{days}日後" if self.language == "ja" else f"in {days}d")

            # Dependencies
            if t.dependencies:
                parts.append(
                    f"依存{len(t.dependencies)}件"
                    if self.language == "ja"
                    else f"deps:{len(t.dependencies)}"
                )

            lines.append(" ".join(parts))

        return "\n".join(lines)

    def _parse_portfolio_response(
        self, response: str, tasks: list["Task"]
    ) -> HolisticResult:
        """Parse LLM response into HolisticResult."""
        import json

        task_map = {t.short_id: t.id for t in tasks}

        # Try to extract JSON from response
        result = HolisticResult()
        llm_reasons: dict[str, str] = {}  # task_id -> reason from LLM

        try:
            # Find JSON in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())

                # Parse recommended order (supports both old and new format)
                if "order" in data and isinstance(data["order"], list):
                    for item in data["order"]:
                        if isinstance(item, dict):
                            # New format: {"id": "...", "reason": "..."}
                            tid = item.get("id", "")
                            reason = item.get("reason", "")
                            full_id = task_map.get(tid, tid)
                            if full_id:
                                result.recommended_order.append(full_id)
                                if reason:
                                    llm_reasons[full_id] = reason
                        elif isinstance(item, str):
                            # Old format: just task ID
                            full_id = task_map.get(item, item)
                            if full_id:
                                result.recommended_order.append(full_id)

                # Parse groups
                if "groups" in data and isinstance(data["groups"], list):
                    for group in data["groups"]:
                        if isinstance(group, list) and len(group) >= 2:
                            name = str(group[0])
                            task_ids = [
                                task_map.get(tid, tid)
                                for tid in group[1]
                                if isinstance(group[1], list)
                            ]
                            if task_ids:
                                result.task_groups.append((name, task_ids))

                # Parse insights
                if "insights" in data and isinstance(data["insights"], list):
                    for insight in data["insights"]:
                        if insight:
                            result.insights.append(
                                PortfolioInsight(
                                    insight_type="general",
                                    description=str(insight),
                                )
                            )

                # Parse warnings
                if "warnings" in data and isinstance(data["warnings"], list):
                    result.warnings = [str(w) for w in data["warnings"] if w]

                # Parse assessment
                if "assessment" in data:
                    result.overall_assessment = str(data["assessment"])
            else:
                # No JSON found, use response as free-form text
                result.overall_assessment = response.strip()

        except (json.JSONDecodeError, KeyError, TypeError):
            # If JSON parsing fails, treat response as free-form text
            result.overall_assessment = response.strip()

        # Fallback: if no order parsed, use original order
        if not result.recommended_order:
            result.recommended_order = [t.id for t in tasks]

        # Fallback: if no assessment, generate basic one
        if not result.overall_assessment:
            if self.language == "ja":
                result.overall_assessment = f"{len(tasks)}件のタスクを分析しました。"
            else:
                result.overall_assessment = f"Analyzed {len(tasks)} tasks."

        # Store LLM reasons in result for later use
        result._llm_reasons = llm_reasons  # type: ignore[attr-defined]

        return result

    def _build_task_context(self, task: "Task", all_tasks: list["Task"]) -> str:
        """Build context string for a task."""
        pm = self._prompt_manager

        lines = [
            f"{pm.get('task_name')}: {task.title}",
            f"{pm.get('priority')}: {task.priority.value}",
            f"{pm.get('status')}: {task.status.value}",
        ]

        if task.description:
            lines.append(f"{pm.get('description')}: {task.description}")

        if task.due_date:
            from datetime import datetime

            days = (task.due_date - datetime.now()).days
            if days < 0:
                lines.append(pm.format("deadline_overdue", days=days * -1))
            elif days == 0:
                lines.append(pm.get("deadline_today"))
            else:
                lines.append(pm.format("deadline_days", days=days))

        if task.estimated_hours:
            lines.append(pm.format("estimated_hours", hours=task.estimated_hours))

        # Check dependencies
        blocking = [t for t in all_tasks if t.id in task.dependencies and t.is_open]
        if blocking:
            lines.append(pm.format("blocking", count=len(blocking)))

        blocked_by = [t for t in all_tasks if task.id in t.dependencies and t.is_open]
        if blocked_by:
            lines.append(pm.format("blocked_by", count=len(blocked_by)))

        return "\n".join(lines)


def is_llama_available() -> bool:
    """Check if llama-cpp-python is available."""
    return LLAMA_AVAILABLE
