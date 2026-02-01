"""LLM-based AI provider using llama-cpp-python."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..base import AIProvider, AnalysisResult, PlanResult, SuggestionResult
from ..model_manager import DEFAULT_MODEL, ModelManager
from .rule_based import RuleBasedProvider

# Language-specific prompt templates
PROMPTS = {
    "en": {
        "analyze_system": "You are a task management assistant. Analyze the task and explain why it should be prioritized.\nBe concise (1-2 sentences).",
        "analyze_user": "Analyze this task and explain its priority:\n\n{context}\n\nCurrent priority score: {score}/100\n\nWhy should this task be prioritized? Give a brief explanation:",
        "suggest_system": "You are a task assistant. Give 1-2 brief action suggestions for the task.\nBe specific and actionable.",
        "suggest_user": "Task: {title}\n{context}\n\nGive 1-2 brief suggestions (one per line):",
        "reason_system": "You are a task assistant. Explain briefly why this task should be done now.\nOne sentence only.",
        "reason_user": "Task: {title}\n{context}\n\nWhy do this task now?",
        "task_name": "Task",
        "priority": "Priority",
        "status": "Status",
        "description": "Description",
        "deadline_overdue": "Deadline: {days} days overdue",
        "deadline_today": "Deadline: today",
        "deadline_days": "Deadline: in {days} days",
        "estimated_hours": "Estimated time: {hours} hours",
        "blocking": "Blocking: {count} tasks not completed",
        "blocked_by": "Waiting for this task: {count} tasks",
    },
    "ja": {
        "analyze_system": "あなたはタスク管理アシスタントです。タスクを分析し、なぜ優先すべきかを説明してください。\n簡潔に（1-2文で）書いてください。",
        "analyze_user": "このタスクを分析し、優先度の理由を説明してください：\n\n{context}\n\n現在の優先度スコア: {score}/100\n\nなぜこのタスクを優先すべきですか？簡潔に説明してください：",
        "suggest_system": "あなたはタスク管理アシスタントです。タスクに対する1-2個の具体的なアクション提案をしてください。\n具体的で実行可能なものにしてください。",
        "suggest_user": "タスク: {title}\n{context}\n\n1-2個の提案を書いてください（1行ずつ）：",
        "reason_system": "あなたはタスクアシスタントです。このタスクを今やるべき理由を簡潔に説明してください。\n一文のみで。",
        "reason_user": "タスク: {title}\n{context}\n\nなぜ今このタスクをやるべき？",
        "task_name": "タスク名",
        "priority": "優先度",
        "status": "ステータス",
        "description": "説明",
        "deadline_overdue": "期限: {days}日超過",
        "deadline_today": "期限: 今日",
        "deadline_days": "期限: {days}日後",
        "estimated_hours": "見積時間: {hours}時間",
        "blocking": "ブロック中: {count}個のタスクが未完了",
        "blocked_by": "このタスクを待っている: {count}個",
    },
}

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
            return rule_result

        # Build context about the task
        context = self._build_task_context(task, all_tasks)

        # Get language-specific prompts
        p = PROMPTS[self.language]
        system_prompt = p["analyze_system"]
        user_prompt = p["analyze_user"].format(context=context, score=rule_result.score)

        prompt = f"""<|system|>
{system_prompt}
</s>
<|user|>
{user_prompt}
</s>
<|assistant|>
"""

        response = self._generate(prompt, max_tokens=150)
        if response:
            # Clean up the response
            reasoning = response.strip()
            # Remove any incomplete sentences at the end
            if reasoning and not reasoning.endswith(('。', '.', '!', '?')):
                last_period = max(reasoning.rfind('。'), reasoning.rfind('.'))
                if last_period > 0:
                    reasoning = reasoning[:last_period + 1]

            if reasoning and len(reasoning) > 10:
                # Generate suggestions using LLM
                suggestions = self._generate_suggestions_llm(task, context)

                return AnalysisResult(
                    task_id=task.id,
                    score=rule_result.score,
                    reasoning=f"🤖 {reasoning}",
                    suggestions=suggestions or rule_result.suggestions,
                )

        return rule_result

    def _generate_suggestions_llm(self, task: "Task", context: str) -> list[str]:
        """Generate action suggestions using LLM."""
        p = PROMPTS[self.language]
        system_prompt = p["suggest_system"]
        user_prompt = p["suggest_user"].format(title=task.title, context=context)

        prompt = f"""<|system|>
{system_prompt}
</s>
<|user|>
{user_prompt}
</s>
<|assistant|>
"""
        response = self._generate(prompt, max_tokens=100)
        if response:
            lines = [line.strip() for line in response.strip().split('\n') if line.strip()]
            # Clean up suggestions
            suggestions = []
            for line in lines[:2]:
                # Remove numbering
                line = re.sub(r'^[\d\.\-\*]+\s*', '', line)
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
        rule_suggestions = self._fallback.suggest_tasks(
            tasks, hours_available, energy_level, count
        )

        llm = self._get_llm()
        if llm is None:
            return rule_suggestions

        p = PROMPTS[self.language]

        # Enhance each suggestion with LLM reasoning
        enhanced_suggestions = []
        for suggestion in rule_suggestions[:count]:
            task = suggestion.task
            context = self._build_task_context(task, tasks)

            system_prompt = p["reason_system"]
            user_prompt = p["reason_user"].format(title=task.title, context=context)

            prompt = f"""<|system|>
{system_prompt}
</s>
<|user|>
{user_prompt}
</s>
<|assistant|>
"""
            response = self._generate(prompt, max_tokens=80)
            reason = suggestion.reason  # Default to rule-based reason

            if response:
                cleaned = response.strip()
                # Take first sentence only
                for sep in ['。', '.', '\n']:
                    if sep in cleaned:
                        cleaned = cleaned.split(sep)[0] + ('。' if sep == '。' else '')
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

    def _build_task_context(self, task: "Task", all_tasks: list["Task"]) -> str:
        """Build context string for a task."""
        p = PROMPTS[self.language]

        lines = [
            f"{p['task_name']}: {task.title}",
            f"{p['priority']}: {task.priority.value}",
            f"{p['status']}: {task.status.value}",
        ]

        if task.description:
            lines.append(f"{p['description']}: {task.description}")

        if task.due_date:
            from datetime import datetime
            days = (task.due_date - datetime.now()).days
            if days < 0:
                lines.append(p["deadline_overdue"].format(days=days * -1))
            elif days == 0:
                lines.append(p["deadline_today"])
            else:
                lines.append(p["deadline_days"].format(days=days))

        if task.estimated_hours:
            lines.append(p["estimated_hours"].format(hours=task.estimated_hours))

        # Check dependencies
        blocking = [t for t in all_tasks if t.id in task.dependencies and t.is_open]
        if blocking:
            lines.append(p["blocking"].format(count=len(blocking)))

        blocked_by = [t for t in all_tasks if task.id in t.dependencies and t.is_open]
        if blocked_by:
            lines.append(p["blocked_by"].format(count=len(blocked_by)))

        return "\n".join(lines)


def is_llama_available() -> bool:
    """Check if llama-cpp-python is available."""
    return LLAMA_AVAILABLE
