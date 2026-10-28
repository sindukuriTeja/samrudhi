"""Agent runtime: executes a single agent against a deliverable.

Builds the role-aware prompt from the deliverable context, calls the LLM
router (Ollama or mock), records the run with telemetry, stores the output on
the deliverable, and emits a SAPI evaluation + ledger entry.
"""
from __future__ import annotations

import time

from ..agents.registry import Agent, get_agent
from ..db import Database
from ..llm.router import LLMRouter
from ..sapi.scorecard import evaluate_run

# Per-stage prompt templates. {ctx} is filled with the deliverable context.
_STAGE_PROMPTS: dict[str, str] = {
    "intake": (
        "Produce the CLIENT BRIEF for this content deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\nTopic: {topic}\n\n"
        "Client context:\n{client}\n\n"
        "Turn this into a complete, unambiguous brief a production team can "
        "execute against, including objective, audience, channels, tone, "
        "success measures and explicit guardrails."
    ),
    "planning": (
        "You are {agent_name} in the PLANNING stage. {focus}\n\n"
        "Deliverable: {title}\nContent type: {ctype}\nTopic: {topic}\n\n"
        "Client context:\n{client}\n\n"
        "Approved brief:\n{brief}\n"
    ),
    "research": (
        "Produce the HEALTHCARE RESEARCH dossier for this deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\nTopic: {topic}\n\n"
        "Client context:\n{client}\n\n"
        "Approved brief:\n{brief}\n\n"
        "Strategy:\n{strategy}\n\n"
        "Provide verified key facts (each cited to a source), a source list, "
        "explicit claim-risk notes for the screening agent, and any gaps. "
        "Only state what a source supports; mark anything unsupported."
    ),
    "drafting": (
        "Write the COPY for this deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\nTopic: {topic}\n\n"
        "Client context:\n{client}\n\n"
        "Approved brief:\n{brief}\n\n"
        "Strategy:\n{strategy}\n\n"
        "Verified research:\n{research}\n\n"
        "Produce a hook, body, call to action, hashtags and a compliance "
        "note. Use only research-backed facts. No outcome guarantees."
    ),
    "creative": (
        "Produce the CREATIVE BRIEF / production specification for this "
        "deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\nTopic: {topic}\n\n"
        "Client context:\n{client}\n\n"
        "Copy:\n{copy}\n\n"
        "Specify visual concept, layout, hierarchy, brand palette, type, logo "
        "placement, platform specs, exports and accessibility. No patient "
        "imagery or before/after."
    ),
    "qa": (
        "Run the {QA_KIND} for this deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\n\n"
        "Client context:\n{client}\n\n"
        "Copy:\n{copy}\n\n"
        "Creative:\n{creative}\n\n"
        "Research dossier:\n{research}\n\n"
        "Produce a structured report with per-check PASS/FAIL results and "
        "evidence, plus a clear verdict."
    ),
    "assurance": (
        "Independently evaluate this finished deliverable. You did NOT author "
        "it.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\n\n"
        "Client context:\n{client}\n\n"
        "Copy:\n{copy}\n\n"
        "Creative:\n{creative}\n\n"
        "Research:\n{research}\n\n"
        "Technical QA report:\n{qa}\n\n"
        "Clinical screening:\n{screening}\n\n"
        "Score output quality, clinical compliance, technical QA, policy and "
        "cross-client data isolation. Explicitly verify the critical safety "
        "gates. Issue APPROVED FOR HUMAN REVIEW or REJECTED with evidence."
    ),
    "publish": (
        "Record the PUBLICATION of this approved deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\n\n"
        "Client context:\n{client}\n\n"
        "Copy:\n{copy}\n\n"
        "Assurance verdict:\n{assurance}\n\n"
        "Produce a publication record: status, channel, scheduled time, "
        "version, the full approval trail, and post-publish handoff. Only the "
        "approved version is released."
    ),
    "reporting": (
        "Produce the CLIENT PERFORMANCE REPORT for this deliverable.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\n\n"
        "Client context:\n{client}\n\n"
        "Copy:\n{copy}\n\n"
        "Published record:\n{published}\n\n"
        "Provide a performance snapshot (reach, engagement, enquiries, cost "
        "per deliverable) vs account median, evidence-based observations, and "
        "next-step recommendations. Mark it pending external approval."
    ),
    "improvement": (
        "Analyse this completed deliverable lifecycle and produce the "
        "IMPROVEMENT & LEARNING report.\n\n"
        "Deliverable: {title}\n\n"
        "Client context:\n{client}\n\n"
        "All stage outputs:\n{all_outputs}\n\n"
        "Identify what worked, what to improve (with root cause and "
        "corrective action + owner), and map each to the improvement "
        "lifecycle (Observe→Diagnose→Propose→Test→Approve→Deploy→Monitor)."
    ),
    "executive": (
        "Produce the {EXEC_KIND} for this deliverable's lifecycle.\n\n"
        "Deliverable: {title}\nContent type: {ctype}\n\n"
        "Client context:\n{client}\n\n"
        "Pipeline status:\n{status}\n\n"
        "Summarise status, governance, any decision requested and watch items "
        "for the intended audience."
    ),
}

# Which context fields each stage needs
_STAGE_FIELDS: dict[str, list[str]] = {
    "intake": ["brief"],
    "planning": ["brief"],
    "research": ["brief", "strategy"],
    "drafting": ["brief", "strategy", "research"],
    "creative": ["copy"],
    "qa": ["copy", "creative", "research"],
    "assurance": ["copy", "creative", "research", "qa", "screening"],
    "publish": ["copy", "assurance"],
    "reporting": ["copy", "published"],
    "improvement": ["all_outputs"],
    "executive": ["status"],
}

# Per-agent focus text for the shared planning stage
_PLANNING_FOCUS = {
    "SAM-AG-059": ("Produce a DELIVERY PLAN: sequence the pipeline stages with "
                   "owners, SLAs, dependencies and the human approval gate. "
                   "Estimate workload using standard capacity units."),
    "SAM-AG-076": ("Produce a CONTENT STRATEGY: positioning, ranked strategic "
                   "angles, message hierarchy (lead/support/close), audience "
                   "insight, channel fit and KPIs for this asset."),
    "SAM-AG-077": ("Produce an EDITORIAL CALENDAR: a 4-week schedule of assets "
                   "with formats, channels, cadence, status and QA/approval "
                   "checkpoints for the client's programme."),
}


def _client_block(client: dict) -> str:
    if not client:
        return "(no client context provided)"
    lines = [f"- Name: {client.get('name')}"]
    for k, label in [("specialty", "Specialty"), ("geography", "Geography"),
                     ("tone", "Tone of voice"), ("audience", "Primary audience"),
                     ("channels", "Channels")]:
        if client.get(k):
            lines.append(f"- {label}: {client[k]}")
    if client.get("brand_do"):
        lines.append(f"- Brand DO: {client['brand_do']}")
    if client.get("brand_dont"):
        lines.append(f"- Brand DON'T: {client['brand_dont']}")
    return "\n".join(lines)


class AgentRuntime:
    def __init__(self, db: Database, llm: LLMRouter):
        self.db = db
        self.llm = llm

    # ------------------------------------------------------------------ #
    def run_agent(self, agent: Agent, deliverable: dict, client: dict,
                  qa_kind: str = "TECHNICAL QA",
                  exec_kind: str = "EXECUTIVE BRIEF") -> dict:
        """Execute one agent on a deliverable. Returns the run record."""
        stage = agent.stage or "executive"
        did = deliverable["id"]

        prompt = self._build_prompt(agent, stage, deliverable, client, qa_kind,
                                    exec_kind)
        ctx = {
            "deliverable_id": did,
            "stage": stage,
            "client": client,
            "title": deliverable.get("title", ""),
            "topic": deliverable.get("topic", ""),
            "content_type": deliverable.get("content_type", ""),
        }

        self.db.log(did, agent.id, "run.start",
                    f"stage={stage} provider_target={self.llm.settings.llm_provider}")
        run = self.db.create_run(did, stage, agent.id, status="running",
                                 input_summary=prompt[:500])
        try:
            res = self.llm.generate(agent.system_prompt, prompt, ctx=ctx)
        except Exception as e:  # noqa: BLE001
            self.db.log(did, agent.id, "run.error", str(e), run["id"])
            self.db.finish_run(run["id"], "failed", error=str(e))
            raise

        # store output on the deliverable
        if agent.output_field:
            self.db.update_deliverable(did, **{agent.output_field: res.text})

        # telemetry + ledger
        self.db.log(did, agent.id, "run.complete",
                    f"provider={res.provider} model={res.model} "
                    f"tokens_in={res.tokens_in} tokens_out={res.tokens_out} "
                    f"latency_ms={res.latency_ms}", run["id"])

        # SAPI evaluation of this run (independent of the producing agent)
        evals = evaluate_run(self.db, deliverable, agent, res, run["id"])

        run = self.db.finish_run(
            run["id"], "completed",
            output_summary=res.text[:500],
            provider=res.provider, model=res.model,
            tokens_in=res.tokens_in, tokens_out=res.tokens_out,
            cost_usd=res.cost_usd,
        )
        run["evaluations"] = evals
        run["output"] = res.text
        return run

    # ------------------------------------------------------------------ #
    def _build_prompt(self, agent: Agent, stage: str, deliverable: dict,
                      client: dict, qa_kind: str, exec_kind: str) -> str:
        template = _STAGE_PROMPTS.get(stage, _STAGE_PROMPTS["executive"])
        fields = _STAGE_FIELDS.get(stage, [])

        def val(f: str) -> str:
            if f == "all_outputs":
                parts = []
                for k in ("brief", "plan", "strategy", "calendar", "research",
                          "copy", "creative", "qa_report", "screening",
                          "assurance", "published", "report"):
                    if deliverable.get(k):
                        parts.append(f"### {k}\n{deliverable[k]}")
                return "\n\n".join(parts) or "(no outputs yet)"
            if f == "status":
                return (f"stage={deliverable.get('current_stage')} "
                        f"status={deliverable.get('status')}")
            v = deliverable.get(f)
            return v if v else "(not yet produced)"

        mapping = {
            "title": deliverable.get("title", ""),
            "ctype": deliverable.get("content_type", ""),
            "topic": deliverable.get("topic", ""),
            "client": _client_block(client),
            "QA_KIND": qa_kind,
            "EXEC_KIND": exec_kind,
            "agent_name": agent.name,
            "focus": _PLANNING_FOCUS.get(
                agent.id, "Produce the planning output for this deliverable."),
        }
        for f in fields:
            mapping[f] = val(f)
        # fill template; any missing key defaults gracefully
        try:
            return template.format(**mapping)
        except KeyError:
            # fallback: replace known keys manually
            out = template
            for k, v in mapping.items():
                out = out.replace("{" + k + "}", str(v))
            return out

    # ------------------------------------------------------------------ #
    def run_stage(self, stage: str, deliverable: dict, client: dict,
                  qa_kind: str = "TECHNICAL QA",
                  exec_kind: str = "EXECUTIVE BRIEF") -> list[dict]:
        """Run all agents assigned to a stage (in order). Returns runs."""
        from ..agents.registry import agents_by_stage
        runs = []
        for agent in agents_by_stage(stage):
            run = self.run_agent(agent, deliverable, client, qa_kind, exec_kind)
            runs.append(run)
            deliverable = self.db.get_deliverable(deliverable["id"]) or deliverable
        return runs