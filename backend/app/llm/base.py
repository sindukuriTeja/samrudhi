"""Common LLM result type."""
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)