"""Pipeline engine — the content lifecycle state machine.

Stages (per the pilot operating sequence from Document 01C):

    intake      → Shruti (brief)
    planning    → Yojana (plan) + Disha (strategy) + Kalpana (calendar)
    research    → Anvesh (research)
    drafting    → Lekha (copy)
    creative    → Chitra (creative)
    qa          → Shuddhi (clinical screening) + Pariksha (technical QA)
    assurance   → Gunvatta (independent eval) + Swasthya (compliance)
    approval    → HUMAN GATE (Mitra prepares package; human decides)
    publish     → Prakash (publication record)
    reporting   → Prativedan (client report) + Lagaat (cost note)
    improvement → Medha (improvement & learning)

The engine pauses at `approval` and waits for a human decision. A failed
critical safety gate blocks the pipeline before the approval gate.
"""
from __future__ import annotations

import threading

from ..agents.registry import Agent, agents_by_stage, get_agent
from ..agents.runtime import AgentRuntime
from ..db import Database
from ..sapi.scorecard import _check_critical_gates

STAGES = [
    "intake", "planning", "research", "drafting", "creative",
    "qa", "assurance", "approval", "publish", "reporting", "improvement",
]

# Agents that prepare the approval package (no output field, advisory)
APPROVAL_PREPARERS = ["SAM-AG-004"]  # Mitra


class PipelineEngine:
    def __init__(self, db: Database, runtime: AgentRuntime):
        self.db = db
        self.runtime = runtime
        self._active: set[str] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    def _client(self, deliverable: dict) -> dict:
        cid = deliverable.get("client_id")
        return self.db.get_client(cid) or {} if cid else {}

    # ------------------------------------------------------------------ #
    def start(self, deliverable_id: str) -> dict:
        """Run the pipeline from intake through the approval gate (async)."""
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError(f"deliverable {deliverable_id} not found")
        if d["status"] in ("published", "approved", "rejected", "failed"):
            raise ValueError(f"deliverable is in terminal state {d['status']}")
        with self._lock:
            if deliverable_id in self._active:
                raise ValueError("pipeline already running for this deliverable")
            self._active.add(deliverable_id)
        self.db.update_deliverable(deliverable_id, status="running",
                                   current_stage="intake")
        self.db.log(deliverable_id, "Pravahika", "pipeline.start",
                    "workflow execution started")
        threading.Thread(target=self._run_to_gate, args=(deliverable_id,),
                         daemon=True).start()
        return self.db.get_deliverable(deliverable_id)

    def resume_after_approval(self, deliverable_id: str) -> dict:
        """Continue from publish after a human approved."""
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError("deliverable not found")
        if d["status"] != "approved":
            raise ValueError("deliverable is not in 'approved' state")
        with self._lock:
            self._active.add(deliverable_id)
        self.db.update_deliverable(deliverable_id, status="running",
                                   current_stage="publish")
        self.db.log(deliverable_id, "Pravahika", "pipeline.resume",
                    "human approval received; continuing to publish")
        threading.Thread(target=self._run_publish_path,
                         args=(deliverable_id,), daemon=True).start()
        return self.db.get_deliverable(deliverable_id)

    # ------------------------------------------------------------------ #
    def _run_to_gate(self, deliverable_id: str) -> None:
        try:
            for stage in STAGES:
                if stage == "approval":
                    self._enter_approval_gate(deliverable_id)
                    return
                d = self.db.get_deliverable(deliverable_id)
                if not d or d["status"] in ("rejected", "failed"):
                    return
                self.db.update_deliverable(deliverable_id, current_stage=stage,
                                           status="running")
                self.db.log(deliverable_id, "Pravahika", "stage.start",
                            f"stage={stage}")
                runs = self.runtime.run_stage(stage, d, self._client(d))
                # gate check after QA/assurance
                if stage in ("qa", "assurance"):
                    blocked = self._gate_check(deliverable_id, stage, runs)
                    if blocked:
                        return
                self.db.log(deliverable_id, "Pravahika", "stage.complete",
                            f"stage={stage} runs={len(runs)}")
        except Exception as e:  # noqa: BLE001
            self.db.update_deliverable(deliverable_id, status="failed",
                                       error=str(e))
            self.db.log(deliverable_id, "Pravahika", "pipeline.error", str(e))
        finally:
            with self._lock:
                self._active.discard(deliverable_id)

    def _run_publish_path(self, deliverable_id: str) -> None:
        try:
            for stage in ("publish", "reporting", "improvement"):
                d = self.db.get_deliverable(deliverable_id)
                if not d or d["status"] in ("rejected", "failed"):
                    return
                self.db.update_deliverable(deliverable_id, current_stage=stage,
                                           status="running")
                self.db.log(deliverable_id, "Pravahika", "stage.start",
                            f"stage={stage}")
                self.runtime.run_stage(stage, d, self._client(d))
                self.db.log(deliverable_id, "Pravahika", "stage.complete",
                            f"stage={stage}")
            self.db.update_deliverable(deliverable_id, status="published",
                                       current_stage="complete")
            self.db.log(deliverable_id, "Pravahika", "pipeline.complete",
                        "deliverable published and lifecycle closed")
        except Exception as e:  # noqa: BLE001
            self.db.update_deliverable(deliverable_id, status="failed",
                                       error=str(e))
            self.db.log(deliverable_id, "Pravahika", "pipeline.error", str(e))
        finally:
            with self._lock:
                self._active.discard(deliverable_id)

    # ------------------------------------------------------------------ #
    def _gate_check(self, deliverable_id: str, stage: str,
                    runs: list[dict]) -> bool:
        """Critical safety gate. Returns True if the pipeline is blocked."""
        d = self.db.get_deliverable(deliverable_id)
        text = " ".join(r.get("output", "") for r in runs)
        # also scan the stored stage outputs
        for k in ("copy", "creative", "screening", "qa_report", "assurance"):
            if d.get(k):
                text += "\n" + d[k]
        gates_failed = _check_critical_gates(text)
        if gates_failed:
            self.db.update_deliverable(deliverable_id, status="blocked",
                                       current_stage=stage,
                                       error=f"Critical safety gate failed: {', '.join(gates_failed)}")
            self.db.log(deliverable_id, "Gunvatta", "gate.blocked",
                        f"gates={','.join(gates_failed)}")
            # record feedback so the improvement loop sees it
            for r in runs:
                self.db.add_feedback(
                    deliverable_id=deliverable_id, agent_id=r["agent_id"],
                    run_id=r["id"], evaluator="Gunvatta (Independent Assurance)",
                    dimension="safety", score=0.0,
                    finding=f"Critical safety gate failed: {', '.join(gates_failed)}",
                    severity="critical",
                    evidence="Gate check on stage output text",
                    root_cause="Unsupported or prohibited content detected",
                    corrective_action="Revise content and re-run from this stage",
                    status="open")
            return True
        return False

    # ------------------------------------------------------------------ #
    def _enter_approval_gate(self, deliverable_id: str) -> None:
        d = self.db.get_deliverable(deliverable_id)
        client = self._client(d)
        # Mitra prepares the approval package (advisory run, no output field)
        for aid in APPROVAL_PREPARERS:
            agent = get_agent(aid)
            if agent:
                try:
                    self.runtime.run_agent(
                        agent, d, client,
                        exec_kind="APPROVAL PACKAGE (for human + client reviewer)")
                except Exception:
                    pass
        approval = self.db.create_approval(
            deliverable_id=deliverable_id, stage="approval",
            kind="human_client_approval", status="pending")
        self.db.update_deliverable(deliverable_id, status="awaiting_approval",
                                   current_stage="approval")
        self.db.log(deliverable_id, "Mitra", "approval.requested",
                    f"approval_id={approval['id']}")

    # ------------------------------------------------------------------ #
    def approve(self, deliverable_id: str, reviewer: str, notes: str = "") -> dict:
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError("deliverable not found")
        if d["status"] != "awaiting_approval":
            raise ValueError(f"deliverable is not awaiting approval ({d['status']})")
        pend = self.db.list_approvals(status="pending",
                                      deliverable_id=deliverable_id)
        if not pend:
            raise ValueError("no pending approval found")
        self.db.decide_approval(pend[0]["id"], "approved", reviewer, notes)
        self.db.log(deliverable_id, reviewer, "approval.decided",
                    f"decision=approved notes={notes[:200]}")
        self.db.update_deliverable(deliverable_id, status="approved")
        self.resume_after_approval(deliverable_id)
        return self.db.get_deliverable(deliverable_id)

    def reject(self, deliverable_id: str, reviewer: str, notes: str = "") -> dict:
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError("deliverable not found")
        if d["status"] != "awaiting_approval":
            raise ValueError(f"deliverable is not awaiting approval ({d['status']})")
        pend = self.db.list_approvals(status="pending",
                                      deliverable_id=deliverable_id)
        if not pend:
            raise ValueError("no pending approval found")
        self.db.decide_approval(pend[0]["id"], "rejected", reviewer, notes)
        self.db.log(deliverable_id, reviewer, "approval.decided",
                    f"decision=rejected notes={notes[:200]}")
        self.db.update_deliverable(deliverable_id, status="rejected")
        # record feedback for the improvement loop
        self.db.add_feedback(
            deliverable_id=deliverable_id, agent_id="", run_id="",
            evaluator=reviewer, dimension="human_review", score=40.0,
            finding="Human reviewer rejected the deliverable",
            severity="high", evidence=notes or "(no notes provided)",
            root_cause="Reviewer feedback",
            corrective_action="Revise per reviewer notes and re-run",
            status="open")
        return self.db.get_deliverable(deliverable_id)

    # ------------------------------------------------------------------ #
    def run_agent_adhoc(self, agent_id: str, deliverable_id: str) -> dict:
        """Run a single agent on a deliverable (for the agent sandbox UI)."""
        agent = get_agent(agent_id)
        if not agent:
            raise ValueError(f"unknown agent {agent_id}")
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError("deliverable not found")
        client = self._client(d)
        qa_kind = "CLINICAL SCREENING" if agent.id == "SAM-AG-080" else "TECHNICAL QA"
        exec_kind = ("APPROVAL PACKAGE (for human + client reviewer)"
                     if agent.id == "SAM-AG-004" else "EXECUTIVE BRIEF")
        return self.runtime.run_agent(agent, d, client, qa_kind, exec_kind)

    def run_executive(self, agent_id: str, deliverable_id: str) -> dict:
        """Run an executive/ops agent (no output field) on a deliverable."""
        agent = get_agent(agent_id)
        if not agent:
            raise ValueError(f"unknown agent {agent_id}")
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError("deliverable not found")
        kind = {
            "SAM-AG-001": "EXECUTIVE BRIEF (for Human Board)",
            "SAM-AG-002": "DELIVERY & SLA STATUS REVIEW",
            "SAM-AG-003": "CREATIVE DIRECTION REVIEW",
            "SAM-AG-004": "APPROVAL PACKAGE (for human + client reviewer)",
            "SAM-AG-007": "TECHNICAL HEALTH REPORT",
            "SAM-AG-009": "ANALYTICS & IMPROVEMENT REPORT",
            "SAM-AG-010": "INDEPENDENT ASSURANCE AUDIT NOTE",
            "SAM-AG-158": "DWMS REGISTRY REPORT",
            "SAM-AG-162": "WORKFLOW EXECUTION LOG",
            "SAM-AG-166": "EXECUTION TELEMETRY SUMMARY",
        }.get(agent_id, "EXECUTIVE BRIEF")
        return self.runtime.run_agent(agent, d, self._client(d),
                                      exec_kind=kind)

    # ------------------------------------------------------------------ #
    def deliverable_progress(self, d: dict) -> dict:
        """Compute per-stage progress for the UI."""
        stage_fields = {
            "intake": "brief", "planning": "strategy", "research": "research",
            "drafting": "copy", "creative": "creative", "qa": "qa_report",
            "assurance": "assurance", "approval": None, "publish": "published",
            "reporting": "report", "improvement": "improvement",
        }
        cur = d.get("current_stage")
        status = d.get("status")
        cur_idx = STAGES.index(cur) if cur in STAGES else -1
        stages = []
        for i, s in enumerate(STAGES):
            f = stage_fields[s]
            if status in ("published",) and s != "approval":
                state = "done"
            elif status == "rejected":
                state = "done" if i < cur_idx else ("failed" if i == cur_idx else "pending")
            elif status == "blocked" or status == "failed":
                state = "done" if i < cur_idx else ("failed" if i == cur_idx else "pending")
            elif f and d.get(f):
                state = "done"
            elif s == "approval" and status == "awaiting_approval":
                state = "current"
            elif i == cur_idx and status in ("running", "awaiting_approval"):
                state = "current"
            else:
                state = "pending"
            stages.append({"stage": s, "state": state})
        return {"stages": stages, "status": status, "current_stage": cur}