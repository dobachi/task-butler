"""AI providers for Task Butler."""

from .rule_based import RuleBasedProvider

# LlamaProvider is optional (requires llama-cpp-python)
try:
    from .llama import LlamaProvider, is_llama_available
except ImportError:
    LlamaProvider = None  # type: ignore
    is_llama_available = lambda: False  # noqa: E731

__all__ = [
    "RuleBasedProvider",
    "LlamaProvider",
    "is_llama_available",
]
