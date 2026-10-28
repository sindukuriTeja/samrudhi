"""SAPI — Samrudhi Agent Performance Intelligence.

Implements the blueprint's Agent Performance Scorecard:
    APS = Σ w_i * S_i   (dimensions scored 0-100)
    quality 30 / efficiency 25 / reliability 20 / business 15 / adaptability 10
plus the rule that a failed critical safety gate blocks publication
regardless of the weighted score.
"""
from __future__ import annotations

import time

from ..db import Database
from ..llm.base import LLMResult

WEIGHTS = {
    "quality": 0.30,
    "efficiency": 0.25,
    "reliability": 0.20,
    "business": 0.15,
    "adaptability": 0.10,
}

# Critical safety gates. If any is failed, publication is blocked no matter
# what the weighted APS score is.
CRITICAL_GATES = [
    "unauthorised_medical_claim",
    "cross_client_data_access",
    "unapproved_publication",
    "fabricated_evidence",
]


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _score_quality(res: LLMResult, text: str) -> float:
    """Heuristic quality: length/structure + no-empty + markdown structure."""
    s = 50.0
    if len(text) < 80:
        s -= 30
    elif len(text) > 400:
        s += 10
    # structure: headings, lists, tables
    if "#" in text:
        s += 8
    if "|" in text and "---" in text:
        s += 6
    if "- " in text or "\n1." in text:
        s += 5
    if res.provider == "mock":
        s += 3  # deterministic mock is well-structured by construction
    return _clamp(s)


def _score_efficiency(res: LLMResult) -> float:
    """Heuristic efficiency: latency + token economy."""
    s = 90.0
    if res.latency_ms > 30000:
        s -= 25
    elif res.latency_ms > 10000:
        s -= 10
    total_tokens = res.tokens_in + res.tokens_out
    if total_tokens > 8000:
        s -= 10
    return _clamp(s)


def _score_reliability(res: LLMResult) -> float:
    s = 100.0
    if res.provider == "mock":
        s = 98.0
    if res.meta.get("fallback_reason"):
        s -= 20  # fell back to mock mid-run
    if not res.text.strip():
        s = 0.0
    return _clamp(s)


def _score_business(res: LLMResult, text: str) -> float:
    s = 70.0
    # client-ready signals
    for kw in ("approval", "verdict", "PASS", "APPROVED", "report", "recommend"):
        if kw.lower() in text.lower():
            s += 6
            break
    if "compliance" in text.lower() or "guardrail" in text.lower():
        s += 6
    return _clamp(s)


def _score_adaptability(res: LLMResult) -> float:
    # static per-run heuristic; real system uses feedback-loop history
    return 80.0 if res.provider != "mock" else 75.0


def evaluate_run(db: Database, deliverable: dict, agent, res: LLMResult,
                 run_id: str) -> list[dict]:
    """Score a single run across the 5 SAPI dimensions and persist."""
    text = res.text
    scores = {
        "quality": _score_quality(res, text),
        "efficiency": _score_efficiency(res),
        "reliability": _score_reliability(res),
        "business": _score_business(res, text),
        "adaptability": _score_adaptability(res),
    }
    aps = sum(WEIGHTS[k] * scores[k] for k in WEIGHTS)

    # critical-gate check (heuristic on the produced text)
    gates_failed = _check_critical_gates(text)

    out = []
    for dim, sc in scores.items():
        ev = db.add_evaluation(
            deliverable_id=deliverable["id"], run_id=run_id,
            agent_id=agent.id, dimension=dim, score=round(sc, 1),
            evidence=f"APS dimension '{dim}' for run {run_id}",
        )
        out.append(ev)
    # store the aggregate APS + gate status on the run via a special eval row
    db.add_evaluation(
        deliverable_id=deliverable["id"], run_id=run_id, agent_id=agent.id,
        dimension="APS", score=round(aps, 1),
        evidence=(f"Weighted score {aps:.1f}. "
                  + ("CRITICAL GATE FAILED: " + ",".join(gates_failed)
                     if gates_failed else "All critical gates passed.")),
    )
    out.append({"agent_id": agent.id, "dimension": "APS",
                "score": round(aps, 1), "gates_failed": gates_failed})
    return out


def _check_critical_gates(text: str) -> list[str]:
    """Heuristic gate detection on produced content.

    In production these are enforced by the platform's tool gateway and
    independent assurance; here we screen the output text for the highest-risk
    patterns so the demo demonstrates the gate mechanism end-to-end.
    """
    failed = []
    low = text.lower()
    # outcome-guarantee language in a healthcare context
    guarantee_markers = ["guaranteed cure", "100% success", "guarantees results",
                         "guaranteed results", "cure rate of", "guaranteed outcome"]
    if any(m in low for m in guarantee_markers):
        failed.append("unauthorised_medical_claim")
    # cross-client leakage marker (should never appear)
    if "another client" in low or "client's confidential data from" in low:
        failed.append("cross_client_data_access")
    return failed


def agent_scorecard(db: Database, agent_id: str) -> dict:
    """Aggregate SAPI scorecard for an agent across its runs."""
    evals = db.list_evaluations(agent_id=agent_id)
    by_dim: dict[str, list[float]] = {}
    aps_scores: list[float] = []
    gates_failed_count = 0
    for e in evals:
        d = e["dimension"]
        if d == "APS":
            aps_scores.append(e["score"])
            if "CRITICAL GATE FAILED" in (e.get("evidence") or ""):
                gates_failed_count += 1
        else:
            by_dim.setdefault(d, []).append(e["score"])
    if not aps_scores:
        return {"agent_id": agent_id, "runs": 0, "aps": None,
                "dimensions": {}, "gates_failed": 0}
    dims = {k: round(sum(v) / len(v), 1) for k, v in by_dim.items()}
    return {
        "agent_id": agent_id,
        "runs": len(aps_scores),
        "aps": round(sum(aps_scores) / len(aps_scores), 1),
        "dimensions": dims,
        "weights": WEIGHTS,
        "gates_failed": gates_failed_count,
        "computed_at": time.time(),
    }


def all_scorecards(db: Database, agent_ids: list[str]) -> list[dict]:
    return [agent_scorecard(db, aid) for aid in agent_ids]