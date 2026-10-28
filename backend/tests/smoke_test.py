"""End-to-end smoke test (mock mode): seed, run a deliverable through the
pipeline, approve it, and verify the full lifecycle completes."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# force mock + isolated test db
os.environ["LLM_PROVIDER"] = "mock"
os.environ["DB_PATH"] = str(Path(__file__).resolve().parents[1] / "data" / "test.db")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.llm.router import LLMRouter  # noqa: E402
from app.agents.runtime import AgentRuntime  # noqa: E402
from app.pipeline.engine import PipelineEngine, STAGES  # noqa: E402


def wait_for_status(db, did, want, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = db.get_deliverable(did)
        if d["status"] in want:
            return d
        time.sleep(0.5)
    raise TimeoutError(f"deliverable {did} did not reach {want}")


def main():
    # clean test db
    p = Path(os.environ["DB_PATH"])
    if p.exists():
        p.unlink()
    settings = get_settings()
    db = Database(settings.db_path)

    client = db.create_client(
        name="Test Hospital", specialty="cardiology",
        geography="Hyderabad", tone="warm, professional",
        audience="patients", channels="Instagram, Facebook")
    d = db.create_deliverable(client_id=client["id"],
                              title="Angina awareness carousel",
                              content_type="carousel",
                              topic="recognising angina", brief={})

    llm = LLMRouter(settings)
    runtime = AgentRuntime(db, llm)
    engine = PipelineEngine(db, runtime)

    print("== starting pipeline ==")
    engine.start(d["id"])
    d = wait_for_status(db, d["id"], {"awaiting_approval"})
    print(f"reached approval gate: status={d['status']} stage={d['current_stage']}")

    # verify stage outputs exist
    for f in ("brief", "plan", "strategy", "calendar", "research", "copy",
              "creative", "qa_report", "screening", "assurance"):
        v = d.get(f)
        assert v and len(v) > 50, f"missing/short output field: {f}"
        print(f"  ✓ {f}: {len(v)} chars")

    runs = db.list_runs(deliverable_id=d["id"])
    print(f"runs so far: {len(runs)}")
    agents_used = sorted({r['agent_id'] for r in runs})
    print(f"agents used: {agents_used}")

    print("== approving ==")
    engine.approve(d["id"], "Dr. Reviewer (test)", "looks good")
    d = wait_for_status(db, d["id"], {"published"}, timeout=90)
    print(f"final status: {d['status']} stage={d['current_stage']}")

    for f in ("published", "report", "improvement"):
        v = d.get(f)
        assert v and len(v) > 50, f"missing/short output field: {f}"
        print(f"  ✓ {f}: {len(v)} chars")

    runs = db.list_runs(deliverable_id=d["id"])
    agents_used = sorted({r['agent_id'] for r in runs})
    print(f"total runs: {len(runs)}; distinct agents: {len(agents_used)}")
    print(f"agents: {agents_used}")

    # SAPI scorecards
    from app.sapi.scorecard import agent_scorecard
    sc = agent_scorecard(db, "SAM-AG-082")
    print(f"Lekha scorecard: APS={sc['aps']} dims={sc['dimensions']}")

    # ledger
    ledger = db.list_ledger(d["id"])
    print(f"ledger entries: {len(ledger)}")

    # stats
    print(f"stats: {db.stats()}")

    # test reject path
    d2 = db.create_deliverable(client_id=client["id"],
                               title="Reject test post", content_type="static post",
                               topic="test rejection", brief={})
    engine.start(d2["id"])
    d2 = wait_for_status(db, d2["id"], {"awaiting_approval"})
    engine.reject(d2["id"], "Dr. Reviewer (test)", "off-brand")
    d2 = db.get_deliverable(d2["id"])
    assert d2["status"] == "rejected", d2["status"]
    fb = db.list_feedback(deliverable_id=d2["id"])
    assert fb and fb[0]["finding"].startswith("Human reviewer rejected")
    print("reject path: ✓ (status=rejected, feedback recorded)")

    # test critical-gate block path: craft a deliverable whose copy contains
    # a guarantee marker by running a direct agent with injected text
    print("\n== critical gate test ==")
    from app.llm.mock import MockEngine
    from app.agents.registry import get_agent
    # simulate: run Lekha, then overwrite copy with a bad claim, re-run Shuddhi gate
    d3 = db.create_deliverable(client_id=client["id"],
                               title="Gate test", content_type="static post",
                               topic="gate", brief={})
    # run intake+drafting manually
    c = db.get_client(client["id"])
    dd = db.get_deliverable(d3["id"])
    runtime.run_agent(get_agent("SAM-AG-050"), dd, c)
    dd = db.get_deliverable(d3["id"])
    runtime.run_agent(get_agent("SAM-AG-082"), dd, c)
    # inject a guarantee claim into the copy
    db.update_deliverable(d3["id"], copy="This clinic guarantees a 100% success cure rate for all patients.")
    # run qa stage (Shuddhi + Pariksha) then gate check
    dd = db.get_deliverable(d3["id"])
    runs = runtime.run_stage("qa", dd, c)
    blocked = engine._gate_check(d3["id"], "qa", runs)
    assert blocked, "gate should have blocked"
    d3 = db.get_deliverable(d3["id"])
    assert d3["status"] == "blocked", d3["status"]
    print(f"critical gate: ✓ (status=blocked, error={d3['error']})")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()