# SAMRUDHI Agentic AI — Command Centre

An orchestrated digital workforce for **healthcare content production** (pilot).
SAMRUDHI runs a **194-agent digital workforce** (11 departments) that takes a
client brief and produces review-ready social content — with a **human
approval gate** and a **critical safety gate** (no unauthorised medical
claims, no outcome guarantees) built in. The 24-role pilot pod is wired into
the content pipeline; the remaining 170 roles are registered as logical
positions on the shared model runtime.

```
brief → plan → research → draft → creative → QA → assurance → [HUMAN GATE] → publish → report
```

## What's inside

| Piece | Where | What it does |
|---|---|---|
| **Agent runtime** | `backend/app/agents/` | 194 named agents across 11 departments (Shruti, Yojana, Anvesh, Lekha, Chitra, Shuddhi, Pariksha, Gunvatta, Swasthya, Mitra, Prakash, …) each with a role, prompt, and output field; the 24-role pilot pod is wired into the pipeline |
| **Pipeline engine** | `backend/app/pipeline/` | 11-stage state machine; pauses at the approval gate for a human decision; blocks on failed safety gates |
| **LLM router** | `backend/app/llm/` | Uses local **Ollama**; automatically falls back to a deterministic **mock engine** when the model is unavailable, so the system never dies |
| **SAPI scorecards** | `backend/app/sapi/` | Per-agent performance scores (reliability, quality, efficiency, business, adaptability) with critical-gate checks |
| **API** | `backend/app/api/` | FastAPI — clients, deliverables, runs, approvals, agents, SAPI, feedback, chat, stats |
| **Command Centre UI** | `frontend/` | React (Vite) — Dashboard, Deliverables, Agents, Approvals, Performance, Chat, Clients |
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
executes the content lifecycle; the other 170 roles are registered as
logical positions — same identity/KPI model, invoked when their workflow is
activated.

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
publish, plus the rejection path and the critical-safety-gate block path.
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
| `POST /api/agents/{id}/run` | Run a single agent |
| `GET /api/sapi/scorecards` | Per-agent SAPI performance |
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

## Project layout

```
samrudhi/
├── docker-compose.yml      # ollama + backend + frontend
├── .env.example
├── backend/
│   ├── app/
│   │   ├── agents/         # registry (194 agents, 11 depts) + runtime
│   │   ├── pipeline/       # 11-stage engine
│   │   ├── llm/            # ollama client, mock engine, router
│   │   ├── sapi/           # scorecards + critical gates
│   │   ├── api/            # FastAPI routes
│   │   ├── db.py           # SQLite persistence
│   │   └── main.py         # app factory
│   ├── scripts/seed.py
│   ├── tests/smoke_test.py
│   └── Dockerfile
├── frontend/
│   ├── src/                # React + Vite (9 views)
│   ├── nginx.conf          # SPA fallback + /api proxy
│   └── Dockerfile
└── refs/                   # source-document summaries
```