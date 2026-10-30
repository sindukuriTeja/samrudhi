# Pilot Runbook — Healthcare Content Production

**Scope:** end-to-end pilot of the SAMRUDHI 194-agent workforce on one real
client brief, from intake to a human-approved, review-ready deliverable.
**Owner:** Pilot Lead (human). **Companion index:** [`runbooks.json`](runbooks.json).

The pilot validates three things: (1) the 11-stage pipeline produces a
review-ready deliverable, (2) the safety and human gates actually hold, and
(3) the enriched specialist agents (see `backend/app/agents/enrichments.py`)
improve first-pass acceptance versus the baseline.

---

## 0. Preconditions

| Check | Command | Expected |
|---|---|---|
| Stack is up | `docker compose ps` | ollama, backend, frontend all `Up` |
| API answers | `curl -s localhost:8000/api/health` | `{"status":"ok"}` |
| LLM status | `curl -s localhost:8000/api/llm/status` | `ollama` or `mock` (mock = deterministic fallback, still valid for a dry run) |
| Registry intact | `curl -s localhost:8000/api/agents \| jq length` | `194` |
| Originality gate | `cd backend && python3 scripts/check-agent-originality.py` | reviewed (known template families flagged — see §7) |

> **Mock vs Ollama.** If Ollama is not loaded, the LLM router falls back to a
> deterministic mock engine. Use a mock run for wiring verification only;
> content-quality judgment requires a real model.

## 1. Create the pilot client

```bash
curl -s -X POST localhost:8000/api/clients -H 'content-type: application/json' -d '{
  "name": "Pilot Clinic",
  "specialty": "Cardiology",
  "geography": "Hyderabad, India",
  "tone": "warm, trustworthy, professional",
  "audience": "patients and their families",
  "channels": "Instagram, Facebook",
  "brand_do": "plain language, evidence-backed, empathetic",
  "brand_dont": "no cure claims, no outcome guarantees, no fear-based CTAs"
}'
# → {"id": "CLI-...", ...}   (record the id)
```

## 2. Create the deliverable

```bash
curl -s -X POST localhost:8000/api/deliverables -H 'content-type: application/json' -d '{
  "client_id": "CLI-<from step 1>",
  "title": "World Heart Day — 5 everyday habits for a healthier heart",
  "content_type": "static post",
  "topic": "World Heart Day patient-education post"
}'
# → {"id": "DEL-...", ...}   (record the id)
```

## 3. Run the 11-stage pipeline

```bash
curl -s -X POST localhost:8000/api/deliverables/DEL-<id>/start
```

Watch it live:

- **SSE stream:** `curl -N localhost:8000/api/events` — every agent, stage,
  gate and decision is pushed as it happens.
- **Progress:** `curl -s localhost:8000/api/deliverables/DEL-<id>/progress`
- **Audit ledger:** `curl -s localhost:8000/api/deliverables/DEL-<id>/ledger`

Stages: `intake → planning → research → drafting → creative → qa →
assurance → [HUMAN GATE] → publish → reporting → improvement`.

## 4. Human approval gate (the point of the pilot)

The run **must pause** at the approval gate. Verify it does:

```bash
curl -s localhost:8000/api/approvals | jq '.[] | select(.deliverable_id=="DEL-<id>")'
```

Then record the decision (this is a human judgment, not an API default):

```bash
curl -s -X POST localhost:8000/api/deliverables/DEL-<id>/decision \
  -H 'content-type: application/json' \
  -d '{"reviewer":"Pilot Lead","notes":"Claims checked vs research stage; tone on-brand.","decision":"approve"}'
```

**Pilot pass criteria at the gate:**

1. No unauthorised medical claim survived to the gate (safety gate held).
2. No outcome guarantee / cure language anywhere in the draft.
3. Every factual claim traces to the research stage in the ledger.
4. Tone and brand-Do/Don't from the client record are respected.

If any criterion fails → `decision: "reject"` with notes; the pipeline must
route back and the ledger must record the rejection.

## 5. (Optional) Full workforce cycle

To exercise all 194 agents once against the same deliverable:

```bash
curl -s -X POST localhost:8000/api/workforce/cycle \
  -H 'content-type: application/json' -d '{"deliverable_id":"DEL-<id>"}'
```

Then check SAPI scorecards for the whole workforce:

```bash
curl -s localhost:8000/api/sapi/scorecards | jq 'length'   # expect 194
```

## 6. Enrichment spot-check

All 194 agents carry a specialist craft block (44 core in
`enrichments.py`, 150 additional in `enrichments_extra.py`). Verify one end
to end:

```bash
curl -s localhost:8000/api/agents/SAM-AG-082 | jq '{name, enriched, prompt_len: (.system_prompt|length)}'
# name: "Lekha", enriched: true
```

Compare a Lekha-produced draft (pipeline run) against the same brief run
with enrichment disabled (set `SAMRUDHI_DISABLE_ENRICH=1` in the backend env)
and score first-pass acceptance. **Pilot target:** enriched run reaches
≥90% first-pass acceptance on the pilot brief set.

## 7. Known template families (originality check)

`check-agent-originality.py` flags near-duplicate prompt skeletons. Roles that
sit in the **same department** deliberately share an operational skeleton
(they run the same stage/work-cycle, differentiated by their role-specific
craft block). The specialist-craft blocks lower the full-prompt overlap of
every agent, so the families that once read ~91% (department heads
SAM-AG-005/006/008) and ~82% (CEX SAM-AG-045/048–056) now sit **below** the
40% FAIL threshold. The current top of the chart is the next tier of
within-department pairs, all **known and accepted** for the pilot:

- SAM-AG-109 / 111–115 — Paid Media, SEO & Growth Marketing (~54%)
- SAM-AG-118 / 127 / 130 / 133 — Analytics, Intelligence & Reporting (~53%)
- SAM-AG-137 / 138 / 139 / 145 — Finance & Administration (~53%)
- SAM-AG-023 / 026 — Sales & Business Development (~53%)
- SAM-AG-053 / 054 — Client Experience & Account Management (~53%)

Treat any **new** FAIL line (a pair **across** departments, or a within-
department pair that jumps well above its family's baseline) as a real
duplicate to resolve before merge.

## 8. Pilot exit checklist

- [ ] Deliverable reached `published` (or a documented, recorded rejection)
- [ ] Safety gate blocked at least one seeded bad claim (negative test)
- [ ] Human gate paused the run; decision recorded in ledger
- [ ] 194 SAPI scorecards present and sane (no zero/NaN)
- [ ] Enriched vs baseline first-pass acceptance measured
- [ ] SSE stream showed the full stage sequence with no gaps
- [ ] No agent outside the §7 families flagged by the originality check

**Negative test (required):** create a throwaway deliverable whose brief
asks for an outcome guarantee (e.g. "guarantees cure in 7 days"). The safety
gate must block it and the ledger must show the block. A pilot that cannot
block a bad claim has failed, regardless of output quality.