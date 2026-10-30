# SAMRUDHI Agentic AI — Command Centre

An orchestrated digital workforce for **healthcare content production** (pilot).
SAMRUDHI runs a **194-agent digital workforce** (11 departments) that takes a
client brief and produces review-ready social content — with a **human
approval gate** and a **critical safety gate** (no unauthorised medical
claims, no outcome guarantees) built in.

**Every one of the 194 agents is executable.** The 24-role pilot pod is wired
into the content pipeline; the remaining 170 roles each run their own role
work cycle. A **full workforce cycle** runs all 194 agents in one pass, and a
**real-time event stream** (Server-Sent Events) pushes every agent, stage,
gate and decision to the Command Centre live.

```
brief → plan → research → draft → creative → QA → assurance → [HUMAN GATE] → publish → report
```

## What's inside

| Piece | Where | What it does |
|---|---|---|
| **Agent runtime** | `backend/app/agents/` | 194 named agents across 11 departments (Shruti, Yojana, Anvesh, Lekha, Chitra, Shuddhi, Pariksha, Gunvatta, Swasthya, Mitra, Prakash, …) each with a role, prompt, and KPIs. **All 194 are executable** — pipeline agents run their stage, executives run briefs, everyone else runs a role work cycle. **44 agents carry a specialist-craft enrichment** distilled from the open-source `agency-agents` corpus (see below) |
| **Pipeline engine** | `backend/app/pipeline/` | 11-stage state machine; pauses at the approval gate for a human decision; blocks on failed safety gates |
| **Workforce cycle engine** | `backend/app/pipeline/workforce.py` | Runs the **full 194-agent workforce** in one operational cycle on a deliverable, with per-agent progress, SAPI evaluation and live events |
| **Real-time event bus** | `backend/app/events.py` | In-process pub/sub; every pipeline/workforce/approval event is streamed over **SSE** (`/api/events`) and mirrored to the audit ledger |
| **LLM router** | `backend/app/llm/` | Uses local **Ollama**; automatically falls back to a deterministic **mock engine** when the model is unavailable, so the system never dies |
| **SAPI scorecards** | `backend/app/sapi/` | Per-agent performance scores (reliability, quality, efficiency, business, adaptability) with critical-gate checks — now scored for all 194 agents |
| **API** | `backend/app/api/` | FastAPI — clients, deliverables, runs, approvals, agents, workforce cycles, SAPI, feedback, chat, stats, live events |
| **Command Centre UI** | `frontend/` | React (Vite) — Dashboard, **Live Operations** (real-time feed + 194-agent status board + workforce controls), Deliverables, Agents, Approvals, Performance, Chat, Clients |
| **Docker stack** | `docker-compose.yml` | ollama + backend + frontend, one command |

### The 11 departments (194 canonical agents)

Per the Digital Workforce Master Organisation Register (Document 01C):

| Code | Department | Agents | Head |
|---|---|---|---|
| CEO | CEO Office & Enterprise Strategy | 6 | Arjun (AI CEO) |
| SAL | Sales & Business Development | 13 | Vikram (AI Chief Growth Officer) |
| MKT | Samrudhi Brand & Marketing | 16 | Prerna (Head of Brand & Marketing) |
| CEX | Client Experience & Account Management | 16 | Mitra (AI Chief Client Experience Officer) |
| OPS | Operations & Delivery Management | 18 | Daksh (AI COO) |
| CRT | Creative, Content & Social Media | 22 | Aarya (AI Chief Creative Officer) |
| PMG | Paid Media, SEO & Growth Marketing | 20 | Tejas (AI Head of Performance & Growth) |
| DAT | Analytics, Intelligence & Reporting | 19 | Medha (AI Chief Data & Intelligence Officer) |
| FIN | Finance & Administration | 20 | Niti (AI CFO) |
| TEC | Technology, MCP & AgentOps | 24 | Sutra (AI CTO) |
| GOV | Independent Assurance, Compliance & Agent Performance | 20 | Satya (AI Chief Assurance Agent) |

The **24-role pilot pod** (marked in the registry with a pipeline `stage`)
executes the content lifecycle. The other 170 roles are also fully
executable: each runs a **role work cycle** — a scoped work note against its
registered KPIs and reporting line. A **full workforce cycle** runs all 194
agents in one pass (`POST /api/workforce/cycle`), and every run is scored by
SAPI and streamed live.

## Quick start (Docker — recommended)

Requirements: Docker + Docker Compose.

```bash
cd samrudhi
docker compose up --build
```

Then open **http://localhost:8080**.

What happens on first start:

1. `ollama-init` pulls the model (`llama3.1:8b` by default, ~4.7 GB) into a
   shared volume. First pull can take a while.
2. The backend seeds 3 sample healthcare clients and a sample deliverable.
3. The frontend serves the Command Centre and proxies `/api/*` to the backend.

**Offline / no model?** If Ollama can't pull or serve the model, the backend
automatically falls back to its deterministic mock engine — every agent,
stage, and the full pipeline still work, so you can explore the whole system
without a GPU or internet.

Use a different model:

```bash
OLLAMA_MODEL=qwen2.5:7b docker compose up --build
```

Force the offline mock engine entirely:

```bash
LLM_PROVIDER=mock docker compose up --build
```

## Development setup (no Docker)

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# optional: point at your own Ollama
export OLLAMA_MODEL=llama3.1:8b        # default
# export LLM_PROVIDER=mock             # skip Ollama entirely

python scripts/seed.py                 # seed 3 clients + sample deliverable
uvicorn app.main:app --port 8000 --reload
```

- API: http://localhost:8000/api/health
- OpenAPI docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173 (proxies `/api` to the backend on :8000)

### Tests

```bash
cd backend
python tests/smoke_test.py
```

Runs the full lifecycle in mock mode: pipeline → approval gate → approve →
publish, plus the rejection path, the critical-safety-gate block path, the
full 194-agent workforce cycle, the live event stream, and the specialist
enrichment invariants (all 44 enriched, guardrails last).
Expected final line: `ALL SMOKE TESTS PASSED`.

## Configuration

Copy `.env.example` to `.env` and edit (all variables are optional):

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_MODEL` | `llama3.1:8b` | Model to pull & serve. Smaller/faster: `llama3.1:4b`, `phi3:3.8b` |
| `LLM_PROVIDER` | `ollama` | `ollama` or `mock` (deterministic offline engine) |
| `LLM_FALLBACK_TO_MOCK` | `true` | Fall back to mock per-call when Ollama fails |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address (compose sets `http://ollama:11434`) |
| `DB_PATH` | `data/samrudhi.db` | SQLite location (compose mounts `/data`) |

## API overview

| Method & path | Purpose |
|---|---|
| `GET /api/health` | Liveness + LLM status |
| `GET/POST /api/clients` | List / create clients |
| `GET/POST /api/deliverables` | List / create deliverables |
| `GET /api/deliverables/{id}` | Full deliverable (all stage outputs) |
| `POST /api/deliverables/{id}/start` | Run pipeline to the approval gate |
| `POST /api/deliverables/{id}/decision` | Human approve / reject |
| `GET /api/deliverables/{id}/progress` | Stage progress + runs |
| `GET /api/deliverables/{id}/ledger` | Immutable audit ledger |
| `GET /api/approvals` | Queue awaiting human decision |
| `GET /api/agents`, `GET /api/agents/{id}` | Registry + per-agent detail |
| `POST /api/agents/{id}/run` | Run **any** of the 194 agents on a deliverable |
| `POST /api/workforce/cycle` | Start a full 194-agent workforce cycle on a deliverable |
| `GET /api/workforce/cycle` | Current cycle progress + history |
| `GET /api/events` | **Real-time SSE stream** of all pipeline/workforce/approval events |
| `GET /api/events/history` | Recent event buffer (for late joiners) |
| `GET /api/sapi/scorecards` | Per-agent SAPI performance (all 194) |
| `GET /api/feedback` | Reviewer feedback log |
| `POST /api/chat` | Chat with the system (routed to an agent) |
| `GET /api/stats` | Aggregate stats (runs, tokens, cost) |
| `GET /api/llm/status` | Which LLM provider is active |

## The pipeline (11 stages)

1. **intake** — Shruti turns the brief into a structured content brief
2. **planning** — Yojana (plan) + Disha (strategy) + Kalpana (calendar)
3. **research** — Anvesh gathers evidence and sources
4. **drafting** — Lekha writes the copy
5. **creative** — Chitra produces creative direction
6. **qa** — Shuddhi (clinical screening) + Pariksha (technical QA)
7. **assurance** — Gunvatta (independent eval) + Swasthya (compliance)
8. **approval** — ⚠️ **human gate**: Mitra prepares the package; a human approves or rejects
9. **publish** — Prakash records publication
10. **reporting** — Prativedan (client report) + Lagaat (cost note)
11. **improvement** — Medha (learning & improvement)

**Safety:** a failed critical gate (e.g. an outcome guarantee like
"guarantees a 100% cure rate") sets the deliverable to `blocked` **before**
it ever reaches a human reviewer.

## Specialist-craft enrichments (agency-agents corpus)

44 of the 194 agents carry a **specialist-craft block** — a distilled,
role-specific set of proven practices (decision frameworks, checklists,
hard-won rules) drawn from the open-source
[`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents)
corpus (MIT) and re-authored for healthcare content. The block is appended
between the base role prompt and the governance guardrails, so the guardrails
always remain the final authority.

- **Source of truth:** `backend/app/agents/enrichments.py` (keyed by agent ID)
- **Vendored corpus:** `vendor/agency-agents/` (provenance + export input)
- **A/B switch:** `SAMRUDHI_DISABLE_ENRICH=1` turns all enrichments off, for
  enriched-vs-baseline first-pass-acceptance comparison (see the pilot
  runbook, §6)
- **Coverage:** the core pipeline specialists — research (Anvesh), copy
  (Lekha), creative (Chitra), QA (Shuddhi/Pariksha), assurance (Gunvatta,
  Swasthya), plus brand, SEO, paid-media, analytics, and client-experience
  roles

### Multi-tool agent export

Every one of the 194 agents can be exported as a standalone agent definition
for other AI tooling, in the format each tool expects:

```bash
cd backend
python3 scripts/export_agents.py          # → ../exports/
```

| Tool | Format | Location |
|---|---|---|
| Claude Code | `.md` agent | `exports/claude-code/agents/` |
| Gemini CLI | `.md` agent | `exports/gemini-cli/agents/` |
| Codex | `.toml` agent | `exports/codex/agents/` |
| Cursor | `.mdc` rule | `exports/cursor/rules/` |

Plus `exports/manifest.json` (194 entries: id, name, department, KPIs,
`enriched` flag, per-tool file paths).

### Originality check

Because the workforce is 194 distinct roles, a re-skinned duplicate (new name,
same method) is easy to miss. The originality checker compares every agent
prompt against the whole roster using entity-neutralized 8-word shingle
overlap, so swapping names/identifiers cannot hide a copy:

```bash
cd backend
python3 scripts/check-agent-originality.py            # audit all 194
python3 scripts/check-agent-originality.py SAM-AG-082 # check one
```

Exit code 1 = at least one pair at/above the duplicate threshold
(`ORIGINALITY_FAIL`, default 40%). Known accepted template families (department
heads; CEX responsibility roles) are documented in the pilot runbook, §7.

## Pilot runbook

`runbooks/pilot-healthcare-content.md` is the end-to-end operating procedure
for a real pilot: client → deliverable → 11-stage run → human gate → publish,
plus the full 194-agent workforce cycle, the enriched-vs-baseline A/B
comparison, and the required **negative test** (a seeded bad claim must be
blocked by the safety gate). `runbooks/runbooks.json` is the machine-readable
index of all runbooks.

## Real-time operations

The backend publishes every lifecycle event to an in-process **event bus**
(`backend/app/events.py`) and streams it over **Server-Sent Events** at
`GET /api/events`. Event types include `pipeline.start/complete/failed`,
`stage.start/complete`, `gate.blocked`, `approval.requested/decided`,
`agent.start/done/failed`, and the workforce-cycle set
`cycle.start / cycle.agent.start / cycle.agent.done / cycle.done`.

Every event is also written to the **audit ledger**, so the live feed and the
immutable history always agree. The Command Centre's **Live Operations** view
renders the feed in real time, shows a 194-agent status board that lights up
as each agent completes, and lets you trigger a full workforce cycle on any
deliverable.

To watch the raw stream:

```bash
curl -N http://localhost:8000/api/events
```

## Project layout

```
samrudhi/
├── docker-compose.yml      # ollama + backend + frontend
├── .env.example
├── runbooks/
│   ├── pilot-healthcare-content.md   # end-to-end pilot procedure
│   └── runbooks.json                 # machine-readable runbook index
├── vendor/agency-agents/   # vendored reference corpus (MIT, provenance)
├── exports/                # generated multi-tool agent exports (git-ignorable)
├── backend/
│   ├── app/
│   │   ├── agents/         # registry (194 agents, 11 depts) + runtime + enrichments
│   │   ├── pipeline/       # 11-stage engine + workforce cycle engine
│   │   ├── llm/            # ollama client, mock engine, router
│   │   ├── sapi/           # scorecards + critical gates
│   │   ├── api/            # FastAPI routes
│   │   ├── events.py       # real-time event bus (SSE)
│   │   ├── db.py           # SQLite persistence
│   │   └── main.py         # app factory
│   ├── scripts/seed.py
│   ├── scripts/export_agents.py          # 194 agents → 4 tool formats
│   ├── scripts/check-agent-originality.py
│   ├── tests/smoke_test.py
│   └── Dockerfile
├── frontend/
│   ├── src/                # React + Vite (10 views incl. Live Operations)
│   │   ├── components/     # LiveFeed, WorkforcePanel, AgentStatusBoard
│   │   └── useEventStream.js
│   ├── nginx.conf          # SPA fallback + /api + SSE proxy
│   └── Dockerfile
└── refs/                   # source-document summaries
```