"""FastAPI application for the SAMRUDHI Agentic OS backend."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import get_settings
from .db import get_db
from .llm.router import LLMRouter
from .agents.runtime import AgentRuntime
from .pipeline.engine import PipelineEngine


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
        version="1.0.0",
        description="SAMRUDHI Agentic AI — orchestrated digital workforce for "
                    "healthcare content production (pilot).",
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

    app.state.db = db
    app.state.llm = llm
    app.state.runtime = runtime
    app.state.engine = engine

    app.include_router(router)

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "app": settings.app_name,
            "environment": settings.environment,
            "llm": llm.status(),
        }

    return app


app = create_app()