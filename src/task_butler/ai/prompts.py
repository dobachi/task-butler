"""Prompt management for AI providers.

This module provides a centralized way to manage AI prompts with:
- Default prompts in English and Japanese
- User customization via config.toml
- Placeholder extraction for documentation
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Config

# Default prompts for each language
DEFAULT_PROMPTS = {
    "en": {
        "analyze_system": "You are a task management assistant. Analyze the task and explain why it should be prioritized.\nBe concise (1-2 sentences).",
        "analyze_user": "Analyze this task and explain its priority:\n\n{context}\n\nCurrent priority score: {score}/100\n\nWhy should this task be prioritized? Give a brief explanation:",
        "suggest_system": "You are a task assistant. Give 1-2 brief action suggestions for the task.\nBe specific and actionable.",
        "suggest_user": "Task: {title}\n{context}\n\nGive 1-2 brief suggestions (one per line):",
        "reason_system": "You are a task assistant. Explain briefly why this task should be done now.\nOne sentence only.",
        "reason_user": "Task: {title}\n{context}\n\nWhy do this task now?",
        # Portfolio/holistic analysis prompts
        "portfolio_system": """You are a task management expert. Analyze the task list holistically.""",
        "portfolio_user": """Analyze these {task_count} tasks and provide overall evaluation and insights:

{task_list}

Key points to analyze:
- Which tasks are most urgent
- Are there tasks that can be grouped together
- Any issues to be aware of

Respond concisely in 3-5 sentences:""",
        # UI labels for context building
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
        # Portfolio/holistic analysis prompts
        "portfolio_system": """あなたはタスク管理の専門家です。タスク一覧を俯瞰的に分析してください。""",
        "portfolio_user": """以下の{task_count}件のタスクを分析し、全体的な評価と洞察を簡潔に述べてください。

{task_list}

分析のポイント：
- 緊急性の高いタスクはどれか
- まとめて処理できそうなタスクはあるか
- 注意すべき問題点はあるか

簡潔に3-5文で回答してください：""",
        # UI labels for context building
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

# Prompt categories for documentation
PROMPT_CATEGORIES = {
    "analyze": {
        "description_en": "Task analysis prompts",
        "description_ja": "タスク分析プロンプト",
        "keys": ["analyze_system", "analyze_user"],
    },
    "suggest": {
        "description_en": "Action suggestion prompts",
        "description_ja": "アクション提案プロンプト",
        "keys": ["suggest_system", "suggest_user"],
    },
    "reason": {
        "description_en": "Priority reasoning prompts",
        "description_ja": "優先度理由プロンプト",
        "keys": ["reason_system", "reason_user"],
    },
    "portfolio": {
        "description_en": "Portfolio/holistic analysis prompts",
        "description_ja": "全体分析プロンプト",
        "keys": ["portfolio_system", "portfolio_user"],
    },
    "labels": {
        "description_en": "Context labels (used in prompts)",
        "description_ja": "コンテキストラベル（プロンプト内で使用）",
        "keys": [
            "task_name",
            "priority",
            "status",
            "description",
            "deadline_overdue",
            "deadline_today",
            "deadline_days",
            "estimated_hours",
            "blocking",
            "blocked_by",
        ],
    },
}

# Placeholder documentation
PLACEHOLDER_DOCS = {
    "context": {
        "description_en": "Task details (title, priority, status, deadline, etc.)",
        "description_ja": "タスクの詳細情報（タイトル、優先度、ステータス、期限等）",
    },
    "score": {
        "description_en": "Rule-based priority score (0-100)",
        "description_ja": "ルールベースで計算された優先度スコア (0-100)",
    },
    "title": {
        "description_en": "Task title",
        "description_ja": "タスクのタイトル",
    },
    "days": {
        "description_en": "Number of days (for deadline labels)",
        "description_ja": "日数（期限ラベル用）",
    },
    "hours": {
        "description_en": "Estimated hours",
        "description_ja": "見積時間",
    },
    "count": {
        "description_en": "Number of related tasks",
        "description_ja": "関連タスク数",
    },
    "task_count": {
        "description_en": "Number of tasks being analyzed (for portfolio analysis)",
        "description_ja": "分析対象タスク数（全体分析用）",
    },
    "task_list": {
        "description_en": "Summary list of all tasks (for portfolio analysis)",
        "description_ja": "全タスクのサマリーリスト（全体分析用）",
    },
}


class PromptManager:
    """Manages prompt loading and customization.

    Prompts are loaded with the following precedence:
    1. User-defined prompts in config.toml ([ai.prompts.<language>])
    2. Default prompts (DEFAULT_PROMPTS)

    Example config.toml:
        [ai.prompts.ja]
        analyze_system = "カスタムシステムプロンプト"
        analyze_user = "カスタムユーザープロンプト: {context}"
    """

    def __init__(self, language: str = "ja"):
        """Initialize PromptManager.

        Args:
            language: Language code ('en' or 'ja')
        """
        self.language = language if language in ("en", "ja") else "ja"
        self._prompts: dict[str, str] | None = None

    def _load_prompts(self) -> dict[str, str]:
        """Load prompts from config, falling back to defaults."""
        from ..config import get_config

        # Start with defaults
        prompts = DEFAULT_PROMPTS[self.language].copy()

        # Load custom prompts from config
        try:
            config = get_config()
            ai_config = config.get_ai_config()
            custom_prompts = ai_config.get("prompts", {}).get(self.language, {})

            # Merge custom prompts (override defaults)
            if isinstance(custom_prompts, dict):
                for key, value in custom_prompts.items():
                    if isinstance(value, str) and key in prompts:
                        prompts[key] = value
        except Exception:
            # If config loading fails, use defaults
            pass

        return prompts

    @property
    def prompts(self) -> dict[str, str]:
        """Get all prompts (lazy loaded)."""
        if self._prompts is None:
            self._prompts = self._load_prompts()
        return self._prompts

    def get(self, key: str, default: str = "") -> str:
        """Get a prompt by key.

        Args:
            key: Prompt key (e.g., 'analyze_system', 'suggest_user')
            default: Default value if key not found

        Returns:
            The prompt string
        """
        return self.prompts.get(key, default)

    def format(self, key: str, **kwargs: str | int | float) -> str:
        """Get and format a prompt with placeholder values.

        Args:
            key: Prompt key
            **kwargs: Placeholder values to substitute

        Returns:
            Formatted prompt string
        """
        prompt = self.get(key)
        if prompt and kwargs:
            try:
                return prompt.format(**kwargs)
            except KeyError:
                # Return unformatted if placeholders don't match
                return prompt
        return prompt

    def list_keys(self) -> list[str]:
        """Get all available prompt keys.

        Returns:
            List of prompt keys
        """
        return list(self.prompts.keys())

    def list_placeholders(self, key: str) -> list[str]:
        """Extract placeholder names from a prompt.

        Args:
            key: Prompt key

        Returns:
            List of placeholder names (e.g., ['context', 'score'])
        """
        prompt = self.get(key)
        if not prompt:
            return []
        return re.findall(r"\{(\w+)\}", prompt)

    def is_customized(self, key: str) -> bool:
        """Check if a prompt has been customized by the user.

        Args:
            key: Prompt key

        Returns:
            True if the prompt differs from the default
        """
        current = self.get(key)
        default = DEFAULT_PROMPTS.get(self.language, {}).get(key, "")
        return current != default

    def reload(self) -> None:
        """Reload prompts from config (clears cache)."""
        self._prompts = None

    @staticmethod
    def get_default_prompt(key: str, language: str = "ja") -> str:
        """Get the default prompt for a key.

        Args:
            key: Prompt key
            language: Language code

        Returns:
            Default prompt string
        """
        lang = language if language in ("en", "ja") else "ja"
        return DEFAULT_PROMPTS.get(lang, {}).get(key, "")

    @staticmethod
    def get_all_keys() -> list[str]:
        """Get all available prompt keys (from defaults).

        Returns:
            List of all prompt keys
        """
        # Use 'ja' as reference since both languages have same keys
        return list(DEFAULT_PROMPTS["ja"].keys())

    @staticmethod
    def get_placeholder_info(placeholder: str, language: str = "ja") -> str:
        """Get description for a placeholder.

        Args:
            placeholder: Placeholder name
            language: Language code

        Returns:
            Description string
        """
        info = PLACEHOLDER_DOCS.get(placeholder, {})
        key = f"description_{language}" if language in ("en", "ja") else "description_ja"
        return info.get(key, info.get("description_ja", ""))


# Singleton instance for global access
_prompt_manager: PromptManager | None = None


def get_prompt_manager(language: str | None = None) -> PromptManager:
    """Get the global PromptManager instance.

    Args:
        language: Language code. If None, uses config setting.

    Returns:
        PromptManager instance
    """
    global _prompt_manager

    # Determine language
    if language is None:
        from ..config import get_config

        try:
            language = get_config().get_ai_language()
        except Exception:
            language = "ja"

    # Create or update manager
    if _prompt_manager is None or _prompt_manager.language != language:
        _prompt_manager = PromptManager(language)

    return _prompt_manager
