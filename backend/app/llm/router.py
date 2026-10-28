"""LLM router: picks Ollama or the mock engine, builds role-aware prompts,
and falls back to mock on any Ollama failure so the pipeline never dies."""
from __future__ import annotations

import time

from ..config import Settings
from .base import LLMResult
from .mock import MockEngine
from .ollama import OllamaClient, OllamaError


class LLMRouter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.ollama = OllamaClient(settings.ollama_base_url,
                                   settings.ollama_model,
                                   settings.ollama_timeout)
        self.mock = MockEngine()
        self._ollama_ok: bool | None = None
        self._ollama_checked_at: float = 0.0

    # ---------------- health ---------------- #
    def ollama_available(self) -> bool:
        # re-check at most every 30s so a late-starting Ollama is picked up
        if self._ollama_ok is None or (time.time() - self._ollama_checked_at) > 30:
            self._ollama_ok = self.ollama.ping()
            self._ollama_checked_at = time.time()
        return self._ollama_ok

    def status(self) -> dict:
        return {
            "provider": self.settings.llm_provider,
            "ollama_url": self.settings.ollama_base_url,
            "ollama_model": self.settings.ollama_model,
            "ollama_reachable": self.ollama_available(),
            "models": self.ollama.list_models() if self.ollama_available() else [],
            "fallback_to_mock": self.settings.llm_fallback_to_mock,
        }

    # ---------------- main entry ---------------- #
    def generate(self, system: str, prompt: str, ctx: dict | None = None,
                 temperature: float = 0.7, max_tokens: int = 1400) -> LLMResult:
        ctx = ctx or {}
        use_ollama = (self.settings.llm_provider == "ollama") and self.ollama_available()
        if use_ollama:
            try:
                res = self.ollama.generate(prompt, system=system,
                                           temperature=temperature,
                                           max_tokens=max_tokens)
                if res.text:
                    return res
                raise OllamaError("empty response from Ollama")
            except OllamaError as e:
                if not self.settings.llm_fallback_to_mock:
                    raise
                # mark ollama down for the cooldown window
                self._ollama_ok = False
                self._ollama_checked_at = time.time()
                res = self.mock.generate(prompt, system=system, ctx=ctx)
                res.meta["fallback_reason"] = str(e)
                return res
        return self.mock.generate(prompt, system=system, ctx=ctx)

    def chat(self, messages: list[dict], ctx: dict | None = None,
             temperature: float = 0.7, max_tokens: int = 1400) -> LLMResult:
        ctx = ctx or {}
        use_ollama = (self.settings.llm_provider == "ollama") and self.ollama_available()
        if use_ollama:
            try:
                res = self.ollama.chat(messages, temperature=temperature,
                                       max_tokens=max_tokens)
                if res.text:
                    return res
                raise OllamaError("empty chat response from Ollama")
            except OllamaError as e:
                if not self.settings.llm_fallback_to_mock:
                    raise
                self._ollama_ok = False
                self._ollama_checked_at = time.time()
                # deterministic fallback for chat
                last_user = next((m["content"] for m in reversed(messages)
                                  if m["role"] == "user"), "")
                res = self.mock.generate(last_user, ctx=ctx)
                res.meta["fallback_reason"] = str(e)
                return res
        # mock chat: answer from the last user message
        last_user = next((m["content"] for m in reversed(messages)
                          if m["role"] == "user"), "")
        return self.mock.generate(last_user, ctx=ctx)