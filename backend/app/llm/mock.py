"""Deterministic offline content engine.

Produces realistic, role-aware, client-specific deliverable content so the
entire 10-stage pipeline is demonstrable with no model downloaded. Output is
seeded by (deliverable, stage) so it is stable and non-repetitive.
"""
from __future__ import annotations

import hashlib
import random

from .base import LLMResult


def _seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16)


class MockEngine:
    provider = "mock"
    model = "samrudhi-deterministic-v1"

    def __init__(self, temperature: float = 0.7, max_tokens: int = 1400):
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _rng(self, did: str, stage: str, agent_id: str = "") -> random.Random:
        return random.Random(_seed(did, stage, agent_id, self.model))

    # ------------------------------------------------------------------ #
    def generate(self, prompt: str, system: str = "",
                 ctx: dict | None = None) -> LLMResult:
        ctx = ctx or {}
        did = ctx.get("deliverable_id", "DLV-0")
        stage = ctx.get("stage", "general")
        client = ctx.get("client", {})
        title = ctx.get("title", "Untitled deliverable")
        topic = ctx.get("topic", "")
        ctype = ctx.get("content_type", "static post")
        name = client.get("name", "the client")
        spec = client.get("specialty", "healthcare")
        geo = client.get("geography", "their region")
        tone = client.get("tone", "warm, trustworthy, professional")
        audience = client.get("audience", "patients and their families")
        channels = client.get("channels", "Instagram, Facebook")
        rnd = self._rng(did, stage, ctx.get("agent", {}).get("id", ""))

        builders = {
            "brief": self._brief,
            "calendar": self._calendar,
            "strategy": self._strategy,
            "research": self._research,
            "copy": self._copy,
            "creative": self._creative,
            "qa": self._qa,
            "screening": self._screening,
            "assurance": self._assurance,
            "publish": self._publish,
            "report": self._report,
            "improvement": self._improvement,
            "executive": self._executive,
            "role": self._role,
            "chat": self._chat,
        }
        fn = builders.get(stage, self._generic)
        if stage == "role":
            text = fn(rnd, title, topic, ctype, name, spec, geo, tone,
                      audience, channels, ctx)
        else:
            text = fn(rnd, title, topic, ctype, name, spec, geo, tone,
                      audience, channels)
        tokens_in = max(40, len((system + prompt)) // 4)
        tokens_out = max(40, len(text) // 4)
        return LLMResult(
            text=text, provider=self.provider, model=self.model,
            tokens_in=tokens_in, tokens_out=tokens_out,
            latency_ms=rnd.randint(120, 480),
            meta={"mock": True},
        )

    # ---------------- stage builders ---------------- #
    def _brief(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        goals = r.sample([
            "Educate {a} about {t} in plain language",
            "Build trust with {a} seeking {t} guidance in {g}",
            "Drive qualified enquiries for {t} services",
            "Position {n} as a trusted {s} partner in {g}",
        ], 3)
        return f"""# Client Brief — {title}

## Client
- **Name:** {name}
- **Specialty:** {spec}
- **Geography:** {geo}
- **Tone of voice:** {tone}
- **Primary audience:** {audience}
- **Channels:** {channels}

## Objective
{goals[0].format(a=audience, t=topic, g=geo, n=name, s=spec)}

## Supporting goals
{chr(10).join('- ' + g.format(a=audience, t=topic, g=geo, n=name, s=spec) for g in goals[1:])}

## Deliverable
- **Type:** {ctype}
- **Topic:** {topic}
- **Success measure:** Clear, accurate, brand-compliant content that a {audience.split(' and ')[0]} can understand without specialist knowledge.

## Constraints & guardrails
- No unsupported clinical or treatment-outcome claims.
- No guarantees of results; no before/after patient imagery.
- All clinical statements must be source-backed (verified by Anvesh, screened by Shuddhi).
- Respect {geo} advertising and platform policy requirements.
- Human + client approval is mandatory before publication.

## Handoff
This brief is the single source of truth for Disha (strategy), Anvesh (research) and Lekha (copy)."""

    def _calendar(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        posts = r.sample([
            "Myth vs. fact", "Patient story (anonymised)", "Expert Q&A",
            "Seasonal health tip", "Service spotlight", "Behind the scenes",
            "FAQ carousel", "Clinician introduction",
        ], 4)
        rows = []
        for i, p in enumerate(posts, 1):
            day = r.randint(1, 28)
            rows.append(f"| W{i} | {p} | {channels.split(',')[0].strip()} | Day {day} | Draft |")
        return f"""# Editorial Calendar — {name}

**Cycle:** Next 4 weeks · **Focus theme:** {topic}

| Week | Format | Channel | Day | Status |
|------|--------|---------|-----|--------|
{chr(10).join(rows)}

## Rhythm
- {len(posts)} scheduled assets across {channels}.
- {ctype} (this deliverable) anchors Week 1 as the hero asset.
- Each asset reuses verified research from Anvesh to keep clinical accuracy consistent.

## Notes for Aarya
- Balance educational and trust-building content ~70/30.
- Reserve 1 slot per week for a reactive/seasonal post.
- All items route through Shuddhi (clinical screen) and Pariksha (technical QA) before approval."""

    def _strategy(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        angles = r.sample([
            "Empathy-first education", "Authority via clinician voice",
            "Myth-busting for {t}".format(t=topic), "Prevention & early action",
            "What to expect (reducing anxiety)", "Local trust & accessibility",
        ], 3)
        return f"""# Content Strategy — {title}

## Positioning
Frame {topic} for {audience} in {geo} using a **{tone}** voice that leads with
empathy and backs every claim with evidence.

## Strategic angles (ranked)
{chr(10).join(f'{i}. {a}' for i, a in enumerate(angles, 1))}

## Message hierarchy
1. **Lead:** A relatable, human moment around {topic}.
2. **Support:** One or two source-backed facts (from Anvesh's research).
3. **Close:** A low-pressure, clear next step (consult, book, learn more).

## Audience insight
{audience} in {geo} most respond to {tone} messaging that avoids jargon and
respects time. Avoid fear-based framing; prefer calm, factual reassurance.

## Channel fit
- **{channels.split(',')[0].strip()}:** {ctype} — visual hook + short caption.
- **{channels.split(',')[1].strip() if ',' in channels else 'Web'}:** longer supporting copy / link.

## KPIs for this asset
- First-pass acceptance ≥ 90%
- Brand & clinical compliance = 100%
- Engagement above account median; enquiries attributed to the post."""

    def _research(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        n = r.randint(4, 6)
        sources = [
            "National clinical guideline (current edition)",
            "Peer-reviewed systematic review",
            "Professional medical society position statement",
            "Government public-health authority guidance",
            "Hospital {s} department clinical protocol".format(s=spec),
        ][:n]
        facts = [
            f"{topic} is best understood when broken into plain-language steps.",
            f"Early, informed conversation with a {spec} professional improves outcomes.",
            f"Common misconceptions about {topic} persist and should be corrected respectfully.",
            f"Individual responses vary — personalised advice is essential.",
            f"Trusted, consistent information reduces anxiety for {audience}.",
        ][:n]
        return f"""# Healthcare Research — {title}

**Topic:** {topic} · **Prepared by:** Anvesh (Research) · **Client:** {name}

## Verified key facts
{chr(10).join(f'{i}. {f}' for i, f in enumerate(facts, 1))}

## Sources (to be cited)
{chr(10).join(f'- [{i}] {s}' for i, s in enumerate(sources, 1))}

## Claim-risk notes (for Shuddhi)
- Facts 1–{min(3,n)} are low-risk and safe to state.
- Any statement about *outcomes, cure rates, or guarantees* is **NOT** supported and must be excluded.
- Patient-specific advice is out of scope; keep content general and direct readers to consult a clinician.

## Gaps / caveats
- No source supports definitive outcome claims for {topic}; do not imply certainty.
- Regional (geo: {geo}) practice variation may apply — flag where relevant.

**Status:** Research complete, source-backed. Ready for Lekha (copy) and Shuddhi (screen)."""

    def _copy(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        hook = r.choice([
            f"Talking about {topic} can feel overwhelming.",
            f"So much of what we hear about {topic} is a myth.",
            f"Your questions about {topic} deserve clear answers.",
        ])
        return f"""# Copy — {title}

**Type:** {ctype} · **Voice:** {tone} · **Audience:** {audience}

## Hook (first line)
"{hook}"

## Body
{hook} At {name}, we believe {audience} deserve information that is honest,
clear and free of jargon. When it comes to {topic}, the most important thing is
to start an informed conversation with a {spec} professional you trust.

Here are a few things worth knowing:
- Start with the basics — understanding {topic} removes a lot of the fear.
- Early, informed guidance makes a real difference.
- You are not alone; many {audience.split(' and ')[0]}s ask exactly these questions.

## Call to action
Book a consultation or message us — we're here to help you take the next step with confidence.

## Hashtags
#HealthAwareness #{spec.replace(' ', '').title()} #{geo.replace(' ', '').title()} #Wellness #TrustedCare

## Compliance note (auto)
No outcome guarantees or treatment claims are made. General educational content only.
Please consult a qualified {spec} professional for personal advice."""

    def _creative(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        palette = r.sample([
            ["#0E7C66", "#F4F9F7", "#123B33"], ["#1B4F72", "#EAF2F8", "#154360"],
            ["#7D3C98", "#F5EEF8", "#4A235A"], ["#B9770E", "#FEF9E7", "#7E5109"],
        ], 1)[0]
        return f"""# Creative Brief — {title}

**Asset:** {ctype} · **Client:** {name}

## Visual concept
A calm, human, {tone} composition centred on {topic}. Use a single clear focal
point (a clinician, a reassuring icon, or a clean typographic headline). Avoid
clinical sterility and avoid stock imagery that looks generic.

## Layout
- **Primary:** {ctype} sized for {channels.split(',')[0].strip()}.
- **Hierarchy:** Hook headline → 1 supporting line → CTA.
- **Safe zones:** Keep text within platform safe areas; no critical text near edges.

## Brand
- **Palette:** {', '.join(palette)}
- **Type:** Clean sans-serif; generous line-height; high contrast for accessibility.
- **Logo:** {name} wordmark bottom-right, min 8% width.

## Production notes (for Chitra)
- Export at platform-native resolution; provide a square + portrait variant.
- Ensure WCAG AA contrast on all text.
- No patient imagery; no before/after; no outcome-implying graphics.

## Deliverables
1. Primary {ctype} (final)
2. Portrait variant
3. Static fallback (no motion) for accessibility."""

    def _qa(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        checks = [
            ("Factual accuracy", "PASS", "All claims trace to Anvesh's verified research."),
            ("Language & grammar", "PASS", "No spelling/grammar defects found."),
            ("Brand alignment", "PASS", "Tone and voice match the approved brief."),
            ("Platform specs", "PASS", "Dimensions, format and safe zones verified."),
            ("Links & CTA", "PASS", "CTA present and functional; links resolve."),
        ]
        rows = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in checks)
        return f"""# Technical QA — {title}

**Reviewer:** Pariksha (Technical QA) · **Asset:** {ctype}

| Check | Result | Note |
|-------|--------|------|
{rows}

## Summary
All technical checks passed. Asset meets platform requirements and brand standards.
No blocking defects. Cleared to proceed to independent assurance (Gunvatta) and
clinical screening (Shuddhi).

## Defects
None.

## Sign-off
Technically QA-approved by Pariksha. Awaiting independent evaluation and human approval."""

    def _screening(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return f"""# Clinical Screening — {title}

**Reviewer:** Shuddhi (Clinical Screening) · **Client:** {name}

## Scope
Screened all clinical and treatment-related statements for unsupported claims,
outcome guarantees, and sensitive medical content.

## Findings
| # | Statement | Risk | Verdict |
|---|-----------|------|---------|
| 1 | General educational framing of {topic} | Low | Cleared |
| 2 | "Consult a {spec} professional" guidance | Low | Cleared |
| 3 | No outcome/cure/guarantee language present | — | Cleared |

## Clinical-risk verdict
**CLEAR** — No unsupported treatment claims, no outcome guarantees, no
inappropriate patient information, no unapproved testimonials.

## Conditions
- Keep content general; do not add patient-specific advice.
- If copy is revised after this screen, re-run screening (Shuddhi) before approval.

## Sign-off
Clinically screened and cleared by Shuddhi. Forward to independent assurance (Gunvatta)."""

    def _assurance(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return f"""# Independent Assurance — {title}

**Evaluator:** Gunvatta (Independent Output Evaluation) + Swasthya (Healthcare Compliance)
**Independence:** Evaluators did not author this content and do not report to the producing agents.

## Evaluation
| Dimension | Result | Evidence |
|-----------|--------|----------|
| Output quality | PASS | Accurate, complete, brand-aligned copy and creative. |
| Clinical compliance | PASS | Shuddhi screen CLEAR; no unsupported claims. |
| Technical QA | PASS | Pariksha all-checks-pass. |
| Policy & platform | PASS | No policy violations detected. |
| Cross-client data isolation | PASS | Only {name} context used. |

## Critical safety gates
- Unauthorised medical claims: **NONE**
- Cross-client data access: **NONE**
- Unapproved publication risk: **NONE**

## Assurance verdict
**APPROVED FOR HUMAN REVIEW.** All critical gates passed. This content is ready
to be presented to the authorised human reviewer and client for final approval.
No score may override a critical gate; none triggered.

## Sign-off
Independently assured by Gunvatta & Swasthya. Awaiting human + client approval."""

    def _publish(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        ts = "2026-11-02 09:30 IST"
        return f"""# Publication Record — {title}

**Publisher:** Prakash (Publishing) · **Client:** {name}

## Release
- **Status:** PUBLISHED (human + client approved)
- **Channel:** {channels}
- **Scheduled:** {ts}
- **Asset version:** Final, approved build (v1)

## Verification
- Only the approved version was released (version-locked).
- Approval trail: Shuddhi (clear) → Pariksha (QA pass) → Gunvatta/Swasthya (assured) → Human + Client (approved).
- No unapproved content was published.

## Post-publish
- Monitoring handed to Drishti (Analytics) for engagement tracking.
- Prativedan (Reporting) will include this asset in the client report.

## Sign-off
Published by Prakash under the approved release gate."""

    def _report(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        reach = r.randint(8000, 42000)
        eng = r.uniform(2.4, 6.8)
        enr = r.randint(12, 60)
        return f"""# Client Performance Report — {name}

**Prepared by:** Prativedan (Client Reporting) · **Asset:** {title}

## Performance snapshot
| Metric | Value | vs. account median |
|--------|-------|--------------------|
| Reach | {reach:,} | +{r.randint(5, 40)}% |
| Engagement rate | {eng:.1f}% | +{r.randint(2, 15)}% |
| Qualified enquiries | {enr} | +{r.randint(0, 20)}% |
| Cost per accepted deliverable | ₹{r.randint(180, 420)} | within budget |

## Observations
- The {ctype} on {topic} performed above the account median on reach and engagement.
- Enquiries were driven primarily by the clear, low-pressure CTA.
- No compliance or clinical issues were reported post-publish.

## Recommendations
- Replicate the empathy-first framing for the next {spec} topic.
- Test a portrait variant for higher feed retention.
- Schedule a follow-up FAQ asset within 2 weeks to extend the content series.

## Sign-off
Report validated by Medha (Analytics) and ready for client presentation."""

    def _improvement(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return f"""# Improvement & Learning — {title}

**Analyst:** Medha (Analytics) + Satya (Assurance) + Sutra (AgentOps)

## What worked
- Source-backed research (Anvesh) reduced clinical rework to zero this cycle.
- The independent assurance gate caught no issues, indicating strong upstream quality.

## What to improve
| Area | Observation | Corrective action | Owner |
|------|-------------|-------------------|-------|
| Cycle time | Draft→QA handoff took longer than target | Add a lightweight draft-readiness checklist | Aarya |
| Cost | Token usage on research stage above baseline | Tighten research prompt scope | Sutra |
| Feedback | 1 minor tone note from reviewer | Add tone examples to the copy system prompt | Lekha |

## Improvement lifecycle
Observe → Diagnose → Propose → Test → Approve → Deploy → Monitor.
All changes above are low-risk and follow the preapproved release policy;
material changes would require human approval.

## Outcome
Logged to the Unified Feedback Ledger. No regressions. Agent scorecards updated."""

    def _executive(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return f"""# Executive Brief — {title}

**Prepared by:** Arjun (AI CEO) · **For:** Human Board / Founder

## Status
The content production lifecycle for **{name}** ({spec}, {geo}) is running
end-to-end through the orchestrated AI workforce. This deliverable ({ctype} on
{topic}) has completed research, drafting, QA, clinical screening and
independent assurance, and is awaiting the human + client approval gate.

## Governance
- No autonomous publication; the approval gate is enforced by the platform.
- Independent assurance (Satya's office) reports to the Board, not to delivery.
- All critical safety gates passed; zero unauthorised clinical claims.

## Decision requested
Approve or reject the asset for publication. Approval is logged to the audit
ledger and triggers controlled release by Prakash.

## Watch items
- Monitor cost-per-deliverable against the pilot baseline.
- Track first-pass acceptance rate toward the ≥90% pilot exit target."""

    def _role(self, r, title, topic, ctype, name, spec, geo, tone,
              audience, channels, ctx):
        """Role-aware work output for any of the 194 registered agents.

        Deterministic per (agent, deliverable) so repeated runs are stable,
        while different agents produce different, role-specific content.
        """
        agent = ctx.get("agent") or {}
        aid = agent.get("id", "SAM-AG-000")
        aname = agent.get("name", "Agent")
        role = agent.get("role", "Functional role")
        dept = agent.get("department", "")
        reports = agent.get("reports_to", "the accountable lead")
        kpis = agent.get("kpis") or []
        stage = ctx.get("stage_label", "role work")
        # seed a second RNG on the agent id so each agent's output differs
        ar = random.Random(_seed(aid, ctx.get("deliverable_id", "DLV-0"), "role-v1"))
        kpi_rows = "\n".join(
            f"| {k} | {'On track' if ar.random() > 0.15 else 'Watch'} |"
            for k in kpis[:4]) or "| (no KPIs registered) | — |"
        actions = r.sample([
            f"Reviewed the current {ctype} workstream for {name} and validated it against the approved brief.",
            f"Cross-checked {topic} outputs for {name} against department standards and flagged nothing material.",
            f"Updated the {role} register with this cycle's evidence and handoff notes for {reports}.",
            f"Prepared a readiness note for {name}'s {topic} asset, confirming scope, guardrails and next owner.",
            f"Ran a spot-check on {name} deliverables in {geo}; findings logged to the unified feedback ledger.",
        ], 3)
        watch = r.choice([
            "No material risks identified this cycle.",
            "Monitor cost-per-deliverable against the pilot baseline.",
            "Track first-pass acceptance toward the ≥90% target.",
            "Watch SLA headroom on the next intake batch.",
        ])
        return f"""# {role} — Cycle Work Note

**Agent:** {aname} ({aid}) · **Department:** {dept}
**Cycle context:** {name} ({spec}, {geo}) · asset "{title}" ({ctype}, {topic})

## Work performed this cycle
{chr(10).join('- ' + a for a in actions)}

## KPI check (this cycle)
| KPI | Status |
|-----|--------|
{kpi_rows}

## Output & handoff
- Output produced to the defined standard and handed to **{reports}**.
- Only the approved {name} client context was used (cross-client isolation held).
- No clinical claims, outcome guarantees or unverified sources introduced.

## Watch items
- {watch}

**Status:** {stage} complete for this cycle. Ready for the next pipeline event or human review."""

    def _chat(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return (f"Here's a quick status: {title} is moving through the pipeline. "
                f"Research and copy are done, QA and clinical screening passed, and "
                f"independent assurance cleared it. It's now waiting at the human "
                f"approval gate. Once you approve, Prakash will publish to {channels}. "
                f"Want me to pull up the full QA report or the assurance verdict?")

    def _generic(self, r, title, topic, ctype, name, spec, geo, tone, audience, channels):
        return f"""# {title}

Prepared for {name} ({spec}, {geo}) on the topic of {topic}.
Voice: {tone}. Audience: {audience}. Channels: {channels}.

This is a deterministic placeholder produced by the SAMRUDHI mock engine.
Connect Ollama (LLM_PROVIDER=ollama) to generate live model output for this stage."""