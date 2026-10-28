"""LLM abstraction: Ollama (local) with a deterministic mock fallback.

The mock engine produces realistic, role-aware content so the entire
pipeline is demonstrable end-to-end with no model downloaded.
"""
from .base import LLMResult
from .mock import MockEngine
from .ollama import OllamaClient
from .router import LLMRouter

__all__ = ["LLMResult", "MockEngine", "OllamaClient", "LLMRouter"]