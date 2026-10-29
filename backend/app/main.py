"""FastAPI application for the SAMRUDHI Agentic OS backend."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .agents.runtime import AgentRuntime
from .api.routes import router
from .config import get_settings
from .db import get_db
from .events import get_event_bus
from .llm.router import LLMRouter
from .pipeline.engine import PipelineEngine
from .pipeline.workforce import WorkforceEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # warm the db
    get_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.1.0",
        description="SAMRUDHI Agentic AI — orchestrated digital workforce for "
                    "healthcare content production (pilot). All 194 registered "
                    "agents are executable, with a real-time event stream.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # shared singletons
    db = get_db()
    llm = LLMRouter(settings)
    runtime = AgentRuntime(db, llm)
    engine = PipelineEngine(db, runtime)
    workforce = WorkforceEngine(db, runtime)
    bus = get_event_bus()

    # persist every real-time event to the audit ledger (global events use
    # deliverable_id "" so they are queryable but not tied to one deliverable)
    def _persist(event: dict) -> None:
        db.log(event.get("deliverable_id") or "",
               event.get("agent_id") or "",
               f"rt.{event.get('type', 'event')}",
               event.get("detail", "")[:500])

    bus.on_event = _persist

    app.state.db = db
    app.state.llm = llm
    app.state.runtime = runtime
    app.state.engine = engine
    app.state.workforce = workforce
    app.state.bus = bus

    app.include_router(router)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "llm": llm.status(),
        }

    # ------------------------------------------------------------------ #
    # Real-time event stream (Server-Sent Events)
    # ------------------------------------------------------------------ #
    @app.get("/api/events")
    async def events(request: Request):
        """Live SSE feed of every pipeline / workforce / approval event."""
        q = bus.subscribe()
        # async generator: SSE frames for this subscriber
        async def gen():
            try:
                yield "event: hello\ndata: {\"type\": \"hello\"}\n\n"
                async for frame in bus.stream(q):
                    if await request.is_disconnected():
                        break
                    yield frame
            finally:
                bus.unsubscribe(q)
        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/api/events/history")
    def events_history(limit: int = 100):
        return {"events": list(bus.history)[-limit:][::-1]}

    return app


app = create_app()