"""Ollama HTTP client (local model server)."""
from __future__ import annotations

import time

import httpx

from .base import LLMResult


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def ping(self) -> bool:
        try:
            # short timeout: a health check must never block the pipeline
            with httpx.Client(base_url=self.base_url, timeout=2.0) as c:
                r = c.get("/api/version")
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            r = self._client().get("/api/tags")
            if r.status_code != 200:
                return []
            return [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return []

    def generate(self, prompt: str, system: str = "", temperature: float = 0.7,
                 max_tokens: int = 1400) -> LLMResult:
        started = time.time()
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            with self._client() as c:
                r = c.post("/api/generate", json=payload)
                if r.status_code != 200:
                    raise OllamaError(f"Ollama HTTP {r.status_code}: {r.text[:300]}")
                data = r.json()
        except httpx.HTTPError as e:
            raise OllamaError(f"Ollama unreachable: {e}") from e
        latency = int((time.time() - started) * 1000)
        # Ollama reports token counts in the response
        return LLMResult(
            text=data.get("response", "").strip(),
            provider="ollama",
            model=self.model,
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency,
            meta={"eval_duration_s": data.get("eval_duration_ns", 0) / 1e9},
        )

    def chat(self, messages: list[dict], temperature: float = 0.7,
             max_tokens: int = 1400) -> LLMResult:
        started = time.time()
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            with self._client() as c:
                r = c.post("/api/chat", json=payload)
                if r.status_code != 200:
                    raise OllamaError(f"Ollama HTTP {r.status_code}: {r.text[:300]}")
                data = r.json()
        except httpx.HTTPError as e:
            raise OllamaError(f"Ollama unreachable: {e}") from e
        latency = int((time.time() - started) * 1000)
        msg = data.get("message", {})
        return LLMResult(
            text=(msg.get("content") or "").strip(),
            provider="ollama",
            model=self.model,
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            latency_ms=latency,
        )