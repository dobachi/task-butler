"""LLM-based AI provider using llama-cpp-python."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from ..base import AIProvider, AnalysisResult, PlanResult, SuggestionResult, TimeSlot
from ..model_manager import ModelManager, DEFAULT_MODEL
from .rule_based import RuleBasedProvider

if TYPE_CHECKING:
    from datetime import datetime
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
    ):
        """Initialize Llama provider.

        Args:
            model_path: Path to GGUF model file. If None, uses model_name.
            model_name: Name of model to use if model_path not specified.
            n_ctx: Context window size.
            n_gpu_layers: Number of layers to offload to GPU.
            verbose: Whether to show verbose output.
        """
        self.model_path = model_path
        self.model_name = model_name
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
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

        # Use a simpler prompt for natural language response
        prompt = f"""<|system|>
You are a task management assistant. Analyze the task and explain why it should be prioritized.
Be concise (1-2 sentences). Write in Japanese.
</s>
<|user|>
Analyze this task and explain its priority:

{context}

Current priority score: {rule_result.score}/100

Why should this task be prioritized? Give a brief explanation:
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
        prompt = f"""<|system|>
You are a task management assistant. Give 1-2 brief action suggestions for the task.
Write in Japanese. Be specific and actionable.
</s>
<|user|>
Task: {task.title}
{context}

Give 1-2 brief suggestions (one per line):
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

        # Enhance each suggestion with LLM reasoning
        enhanced_suggestions = []
        for suggestion in rule_suggestions[:count]:
            task = suggestion.task
            context = self._build_task_context(task, tasks)

            prompt = f"""<|system|>
You are a task assistant. Explain briefly why this task should be done now.
Write in Japanese. One sentence only.
</s>
<|user|>
Task: {task.title}
{context}

Why do this task now?
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
        lines = [
            f"タスク名: {task.title}",
            f"優先度: {task.priority.value}",
            f"ステータス: {task.status.value}",
        ]

        if task.description:
            lines.append(f"説明: {task.description}")

        if task.due_date:
            from datetime import datetime
            days = (task.due_date - datetime.now()).days
            if days < 0:
                lines.append(f"期限: {days * -1}日超過")
            elif days == 0:
                lines.append("期限: 今日")
            else:
                lines.append(f"期限: {days}日後")

        if task.estimated_hours:
            lines.append(f"見積時間: {task.estimated_hours}時間")

        # Check dependencies
        blocking = [t for t in all_tasks if t.id in task.dependencies and t.is_open]
        if blocking:
            lines.append(f"ブロック中: {len(blocking)}個のタスクが未完了")

        blocked_by = [t for t in all_tasks if task.id in t.dependencies and t.is_open]
        if blocked_by:
            lines.append(f"このタスクを待っている: {len(blocked_by)}個")

        return "\n".join(lines)


def is_llama_available() -> bool:
    """Check if llama-cpp-python is available."""
    return LLAMA_AVAILABLE
