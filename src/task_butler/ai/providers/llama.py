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
        """Analyze a task using LLM or fallback to rules."""
        # First get rule-based analysis as baseline
        rule_result = self._fallback.analyze_task(task, all_tasks)

        # Try LLM enhancement
        llm = self._get_llm()
        if llm is None:
            return rule_result

        # Build context about the task
        context = self._build_task_context(task, all_tasks)

        prompt = f"""<|system|>
あなたはタスク管理アシスタントです。タスクを分析し、優先度スコア（0-100）と理由を提供してください。
</s>
<|user|>
以下のタスクを分析してください：

{context}

JSON形式で回答してください：
{{"score": 数値, "reasoning": "理由", "suggestions": ["提案1", "提案2"]}}
</s>
<|assistant|>
"""

        response = self._generate(prompt)
        if response is None:
            return rule_result

        # Try to parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("score", rule_result.score))
                # Blend with rule-based score (70% LLM, 30% rules)
                blended_score = score * 0.7 + rule_result.score * 0.3
                return AnalysisResult(
                    task_id=task.id,
                    score=round(blended_score, 1),
                    reasoning=data.get("reasoning", rule_result.reasoning),
                    suggestions=data.get("suggestions", rule_result.suggestions),
                )
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        return rule_result

    def suggest_tasks(
        self,
        tasks: list["Task"],
        hours_available: float | None = None,
        energy_level: str | None = None,
        count: int = 5,
    ) -> list[SuggestionResult]:
        """Suggest tasks using LLM or fallback to rules."""
        # Get rule-based suggestions first
        rule_suggestions = self._fallback.suggest_tasks(
            tasks, hours_available, energy_level, count
        )

        llm = self._get_llm()
        if llm is None:
            return rule_suggestions

        # Build task list context
        open_tasks = [t for t in tasks if t.is_open]
        if not open_tasks:
            return []

        task_list = "\n".join(
            f"- {t.short_id}: {t.title} (優先度: {t.priority.value}, "
            f"見積: {t.estimated_hours or '不明'}h)"
            for t in open_tasks[:15]  # Limit for context
        )

        constraints = []
        if hours_available:
            constraints.append(f"利用可能時間: {hours_available}時間")
        if energy_level:
            energy_map = {"low": "低", "medium": "中", "high": "高"}
            constraints.append(f"エネルギーレベル: {energy_map.get(energy_level, energy_level)}")

        prompt = f"""<|system|>
あなたはタスク管理アシスタントです。状況に応じて最適なタスクを提案してください。
</s>
<|user|>
以下のタスクから、取り組むべき順にタスクIDを{count}個選んでください：

タスク一覧：
{task_list}

{chr(10).join(constraints) if constraints else "特に制約なし"}

タスクIDを優先度順にカンマ区切りで回答してください。
</s>
<|assistant|>
"""

        response = self._generate(prompt, max_tokens=128)
        if response is None:
            return rule_suggestions

        # Try to parse task IDs from response
        try:
            # Extract task IDs (8-char hex patterns)
            task_ids = re.findall(r'[a-f0-9]{8}', response.lower())
            if task_ids:
                # Reorder suggestions based on LLM response
                id_to_task = {t.short_id.lower(): t for t in open_tasks}
                llm_ordered = []
                seen = set()
                for tid in task_ids[:count]:
                    if tid in id_to_task and tid not in seen:
                        task = id_to_task[tid]
                        analysis = self._fallback.analyze_task(task, tasks)
                        llm_ordered.append(
                            SuggestionResult(
                                task=task,
                                score=analysis.score,
                                reason=analysis.reasoning,
                                estimated_minutes=(
                                    int(task.estimated_hours * 60)
                                    if task.estimated_hours
                                    else None
                                ),
                            )
                        )
                        seen.add(tid)
                if llm_ordered:
                    return llm_ordered
        except Exception:
            pass

        return rule_suggestions

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
