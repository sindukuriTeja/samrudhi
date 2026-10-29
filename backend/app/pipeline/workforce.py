"""Workforce cycle engine.

Runs the FULL 194-agent digital workforce through one operational cycle on a
deliverable. Every registered agent executes its role work (pipeline agents
run their stage output; everyone else runs a role work-cycle note), in
department order, with real-time events on the bus and per-agent SAPI
evaluation on each run.

This is what makes the whole registry *live*: no agent is a dead row anymore.
"""
from __future__ import annotations

import threading
import time

from ..agents.registry import AGENTS, get_agent
from ..agents.runtime import AgentRuntime
from ..db import Database
from ..events import get_event_bus


class WorkforceEngine:
    def __init__(self, db: Database, runtime: AgentRuntime):
        self.db = db
        self.runtime = runtime
        self.bus = get_event_bus()
        self._active: set[str] = set()
        self._lock = threading.Lock()
        self._last_cycle: dict | None = None

    # ------------------------------------------------------------------ #
    def start(self, deliverable_id: str) -> dict:
        d = self.db.get_deliverable(deliverable_id)
        if not d:
            raise ValueError(f"deliverable {deliverable_id} not found")
        with self._lock:
            if deliverable_id in self._active:
                raise ValueError("a workforce cycle is already running for this deliverable")
            self._active.add(deliverable_id)
        cycle = self.db.create_cycle(total_agents=len(AGENTS))
        self._last_cycle = cycle
        self.bus.emit("cycle.start",
                      f"Full workforce cycle started: {len(AGENTS)} agents",
                      deliverable_id=deliverable_id, cycle_id=cycle["id"],
                      total=len(AGENTS))
        self.db.log(deliverable_id, "Pravahika", "workforce.cycle.start",
                    f"cycle={cycle['id']} agents={len(AGENTS)}")
        threading.Thread(target=self._run_cycle,
                         args=(deliverable_id, cycle["id"]),
                         daemon=True).start()
        return cycle

    def status(self) -> dict:
        c = self._last_cycle
        if c:
            c = self.db.get_cycle(c["id"]) or c
        return {
            "current": c,
            "history": self.db.list_cycles(10),
            "agents_registered": len(AGENTS),
        }

    # ------------------------------------------------------------------ #
    def _run_cycle(self, deliverable_id: str, cycle_id: str) -> None:
        t0 = time.time()
        completed = failed = 0
        try:
            d = self.db.get_deliverable(deliverable_id)
            client = (self.db.get_client(d["client_id"]) or {}) if d and d.get("client_id") else {}
            for i, agent in enumerate(AGENTS, 1):
                d = self.db.get_deliverable(deliverable_id)
                if not d:
                    break
                self.bus.emit("cycle.agent.start",
                              f"Agent {i}/{len(AGENTS)} — {agent.name} ({agent.role})",
                              agent_id=agent.id, name=agent.name,
                              deliverable_id=deliverable_id,
                              cycle_id=cycle_id, index=i,
                              total=len(AGENTS), dept=agent.dept_code)
                try:
                    run = self.runtime.run_agent(
                        agent, d, client,
                        stage_label=f"workforce cycle {cycle_id}")
                    completed += 1
                    self.db.bump_cycle(cycle_id, completed=1)
                    self.bus.emit("cycle.agent.done",
                                  f"{agent.name} completed ({run['provider']}, "
                                  f"{run.get('duration_ms', 0)}ms)",
                                  agent_id=agent.id, name=agent.name,
                                  deliverable_id=deliverable_id,
                                  cycle_id=cycle_id, index=i,
                                  total=len(AGENTS), run_id=run["id"],
                                  aps=next((e["score"] for e in run.get("evaluations", [])
                                            if e["dimension"] == "APS"), None))
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    self.db.bump_cycle(cycle_id, failed=1)
                    self.bus.emit("agent.failed",
                                  f"{agent.name} failed: {e}",
                                  agent_id=agent.id, name=agent.name,
                                  deliverable_id=deliverable_id,
                                  cycle_id=cycle_id, index=i,
                                  total=len(AGENTS), error=str(e))
            self.db.finish_cycle(
                cycle_id, "completed",
                f"{completed}/{len(AGENTS)} agents completed, {failed} failed "
                f"in {int(time.time() - t0)}s")
            self.bus.emit("cycle.done",
                          f"Workforce cycle complete: {completed}/{len(AGENTS)} "
                          f"agents, {failed} failed, {int(time.time() - t0)}s",
                          deliverable_id=deliverable_id, cycle_id=cycle_id,
                          completed=completed, failed=failed,
                          duration_s=int(time.time() - t0))
            self.db.log(deliverable_id, "Pravahika", "workforce.cycle.complete",
                        f"cycle={cycle_id} completed={completed} failed={failed}")
        except Exception as e:  # noqa: BLE001
            self.db.finish_cycle(cycle_id, "failed", str(e))
            self.bus.emit("cycle.failed", f"Workforce cycle failed: {e}",
                          deliverable_id=deliverable_id, cycle_id=cycle_id,
                          error=str(e))
        finally:
            with self._lock:
                self._active.discard(deliverable_id)