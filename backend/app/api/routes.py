"""REST API routes for the SAMRUDHI Agentic OS."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..agents.registry import (AGENTS, all_agents, get_agent, to_dict)
from ..sapi.scorecard import all_scorecards, agent_scorecard, WEIGHTS

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ClientIn(BaseModel):
    name: str
    specialty: str = ""
    geography: str = ""
    tone: str = "warm, trustworthy, professional"
    audience: str = "patients and their families"
    channels: str = "Instagram, Facebook"
    brand_do: str = ""
    brand_dont: str = ""


class DeliverableIn(BaseModel):
    client_id: str
    title: str
    content_type: str = "static post"
    topic: str = ""


class ApprovalDecision(BaseModel):
    reviewer: str = "Human Reviewer"
    notes: str = ""
    decision: str = Field(pattern="^(approve|reject)$")


class AgentRunIn(BaseModel):
    deliverable_id: str


class ChatIn(BaseModel):
    message: str
    agent_id: str = "SAM-AG-001"


# --------------------------------------------------------------------------- #
# Clients
# --------------------------------------------------------------------------- #
@router.get("/clients")
def list_clients(request: Request):
    return request.app.state.db.list_clients()


@router.post("/clients")
def create_client(body: ClientIn, request: Request):
    return request.app.state.db.create_client(**body.model_dump())


@router.get("/clients/{client_id}")
def get_client(client_id: str, request: Request):
    c = request.app.state.db.get_client(client_id)
    if not c:
        raise HTTPException(404, "client not found")
    return c


# --------------------------------------------------------------------------- #
# Deliverables
# --------------------------------------------------------------------------- #
@router.get("/deliverables")
def list_deliverables(request: Request, client_id: str | None = None):
    return request.app.state.db.list_deliverables(client_id)


@router.post("/deliverables")
def create_deliverable(body: DeliverableIn, request: Request):
    db = request.app.state.db
    if not db.get_client(body.client_id):
        raise HTTPException(400, "client_id does not exist")
    d = db.create_deliverable(
        client_id=body.client_id, title=body.title,
        content_type=body.content_type, topic=body.topic or body.title,
        brief={},
    )
    db.log(d["id"], "Shruti", "deliverable.created",
           f"content_type={body.content_type}")
    return d


@router.get("/deliverables/{deliverable_id}")
def get_deliverable(deliverable_id: str, request: Request):
    db = request.app.state.db
    d = db.get_deliverable(deliverable_id)
    if not d:
        raise HTTPException(404, "deliverable not found")
    d["progress"] = request.app.state.engine.deliverable_progress(d)
    d["runs"] = db.list_runs(deliverable_id=deliverable_id)
    return d


@router.get("/deliverables/{deliverable_id}/ledger")
def deliverable_ledger(deliverable_id: str, request: Request):
    return request.app.state.db.list_ledger(deliverable_id)


@router.get("/deliverables/{deliverable_id}/runs")
def deliverable_runs(deliverable_id: str, request: Request):
    return request.app.state.db.list_runs(deliverable_id=deliverable_id)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
@router.post("/deliverables/{deliverable_id}/start")
def start_pipeline(deliverable_id: str, request: Request):
    try:
        return request.app.state.engine.start(deliverable_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/deliverables/{deliverable_id}/decision")
def pipeline_decision(deliverable_id: str, body: ApprovalDecision,
                      request: Request):
    engine = request.app.state.engine
    try:
        if body.decision == "approve":
            return engine.approve(deliverable_id, body.reviewer, body.notes)
        return engine.reject(deliverable_id, body.reviewer, body.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/deliverables/{deliverable_id}/progress")
def deliverable_progress(deliverable_id: str, request: Request):
    d = request.app.state.db.get_deliverable(deliverable_id)
    if not d:
        raise HTTPException(404, "deliverable not found")
    return request.app.state.engine.deliverable_progress(d)


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #
@router.get("/approvals")
def list_approvals(request: Request, status: str | None = None):
    return request.app.state.db.list_approvals(status=status)


# --------------------------------------------------------------------------- #
# Agents
# --------------------------------------------------------------------------- #
@router.get("/agents")
def list_agents(request: Request, tier: str | None = None,
                department: str | None = None):
    out = [to_dict(a) for a in all_agents()]
    if tier:
        out = [a for a in out if a["tier"] == tier]
    if department:
        out = [a for a in out if a["dept_code"] == department]
    return out


@router.get("/agents/{agent_id}")
def get_agent_detail(agent_id: str, request: Request):
    a = get_agent(agent_id)
    if not a:
        raise HTTPException(404, "agent not found")
    d = to_dict(a)
    d["system_prompt"] = a.system_prompt
    d["scorecard"] = agent_scorecard(request.app.state.db, agent_id)
    d["recent_runs"] = request.app.state.db.list_runs(agent_id=agent_id)[:10]
    return d


@router.post("/agents/{agent_id}/run")
def run_agent_adhoc(agent_id: str, body: AgentRunIn, request: Request):
    a = get_agent(agent_id)
    if not a:
        raise HTTPException(404, "agent not found")
    try:
        if a.stage is None:
            return request.app.state.engine.run_executive(agent_id,
                                                          body.deliverable_id)
        return request.app.state.engine.run_agent_adhoc(agent_id,
                                                        body.deliverable_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


# --------------------------------------------------------------------------- #
# SAPI
# --------------------------------------------------------------------------- #
@router.get("/sapi/weights")
def sapi_weights():
    return {"weights": WEIGHTS,
            "formula": "APS = Σ w_i * S_i (dimensions scored 0-100)",
            "critical_gates_block_publication": True}


@router.get("/sapi/scorecards")
def sapi_scorecards(request: Request):
    return all_scorecards(request.app.state.db, [a.id for a in AGENTS])


@router.get("/sapi/scorecards/{agent_id}")
def sapi_scorecard(agent_id: str, request: Request):
    return agent_scorecard(request.app.state.db, agent_id)


# --------------------------------------------------------------------------- #
# Feedback ledger
# --------------------------------------------------------------------------- #
@router.get("/feedback")
def list_feedback(request: Request, agent_id: str | None = None,
                  deliverable_id: str | None = None):
    return request.app.state.db.list_feedback(agent_id=agent_id,
                                              deliverable_id=deliverable_id)


# --------------------------------------------------------------------------- #
# Chat (talk to any agent)
# --------------------------------------------------------------------------- #
@router.post("/chat")
def chat(body: ChatIn, request: Request):
    db = request.app.state.db
    agent = get_agent(body.agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    db.add_chat("user", body.message, agent_id=agent.id)
    # build a short context: recent messages
    history = db.list_chat(limit=12)
    messages = [{"role": "user" if m["role"] == "user" else "assistant",
                 "content": m["content"]} for m in history]
    res = request.app.state.llm.chat(
        messages,
        ctx={"stage": "chat", "client": {}, "title": "conversation",
             "topic": body.message, "content_type": "chat",
             "deliverable_id": agent.id})
    reply = res.text
    db.add_chat("assistant", reply, agent_id=agent.id)
    return {
        "agent_id": agent.id, "agent_name": agent.name, "reply": reply,
        "provider": res.provider, "model": res.model,
    }


@router.get("/chat")
def chat_history(request: Request):
    return request.app.state.db.list_chat()


# --------------------------------------------------------------------------- #
# Stats & LLM
# --------------------------------------------------------------------------- #
@router.get("/stats")
def stats(request: Request):
    s = request.app.state.db.stats()
    s["agents"] = len(AGENTS)
    s["llm"] = request.app.state.llm.status()
    return s


@router.get("/llm/status")
def llm_status(request: Request):
    return request.app.state.llm.status()