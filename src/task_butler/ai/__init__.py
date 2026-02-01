"""AI integration module for Task Butler."""

from .analyzer import TaskAnalyzer
from .base import AIProvider, AnalysisResult, SuggestionResult, PlanResult
from .model_manager import ModelManager
from .planner import DailyPlanner
from .suggester import TaskSuggester

__all__ = [
    "AIProvider",
    "AnalysisResult",
    "SuggestionResult",
    "PlanResult",
    "TaskAnalyzer",
    "TaskSuggester",
    "DailyPlanner",
    "ModelManager",
]


def get_provider(provider_name: str | None = None) -> AIProvider:
    """Get an AI provider instance based on configuration.

    Args:
        provider_name: Override provider name. If None, uses config.

    Returns:
        An AIProvider instance
    """
    from ..config import get_config
    from .providers.rule_based import RuleBasedProvider

    config = get_config()
    ai_config = config.get_ai_config()

    name = provider_name or ai_config.get("provider", "rule_based")

    if name == "llama":
        from .providers.llama import LlamaProvider, is_llama_available

        if is_llama_available():
            llama_config = ai_config.get("llama", {})
            return LlamaProvider(
                model_path=llama_config.get("model_path") or None,
                model_name=llama_config.get("model_name", "tinyllama-1.1b"),
                n_ctx=llama_config.get("n_ctx", 2048),
                n_gpu_layers=llama_config.get("n_gpu_layers", 0),
            )
        # Fall back to rule-based if llama not available
        return RuleBasedProvider()

    elif name == "openai":
        # OpenAI provider not yet implemented, fall back
        return RuleBasedProvider()

    else:
        # Default to rule-based
        analysis_config = ai_config.get("analysis", {})
        return RuleBasedProvider(
            weight_deadline=analysis_config.get("weight_deadline", 0.30),
            weight_dependencies=analysis_config.get("weight_dependencies", 0.25),
            weight_effort=analysis_config.get("weight_effort", 0.20),
            weight_staleness=analysis_config.get("weight_staleness", 0.15),
            weight_priority=analysis_config.get("weight_priority", 0.10),
        )
