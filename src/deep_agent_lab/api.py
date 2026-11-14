import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from langgraph.errors import GraphRecursionError

from deep_agent_lab.rag.models import Hit, SearchRequest
from deep_agent_lab.service import (
    AgentService,
    ReviewRequest,
    RunRequest,
    RunResult,
    ThreadConflict,
    open_checkpointer,
)
from deep_agent_lab.settings import Settings
from deep_agent_lab.storage import Brief

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, model=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configuration = settings if settings is not None else Settings()
        with open_checkpointer(configuration) as checkpointer:
            service = AgentService(configuration, checkpointer, model=model)
            app.state.agent = service
            try:
                yield
            finally:
                service.close()

    app = FastAPI(title="Deep Agent Lab", lifespan=lifespan)

    @app.exception_handler(ThreadConflict)
    async def conflict(request: Request, error: ThreadConflict):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(GraphRecursionError)
    async def limit(request: Request, error: GraphRecursionError):
        return JSONResponse(status_code=422, content={"detail": "The model hit the step limit."})

    @app.exception_handler(Exception)
    async def unavailable(request: Request, error: Exception):
        logger.warning("Agent run failed (%s)", type(error).__name__)
        return JSONResponse(status_code=503, content={"detail": "Agent unavailable. Run doctor."})

    @app.get("/health")
    def health(request: Request):
        rag = request.app.state.agent.rag
        data = (
            {"mode": "live", **rag.health()}
            if rag is not None
            else {"mode": "demo", "status": "ok"}
        )
        return JSONResponse(status_code=200 if data["status"] == "ok" else 503, content=data)

    @app.get("/api/v1/documents")
    def documents(request: Request):
        rag = request.app.state.agent.rag
        if rag is None:
            raise HTTPException(409, "Document listing requires live mode")
        return rag.db.documents()

    @app.post("/api/v1/search", response_model=list[Hit])
    def search(body: SearchRequest, request: Request):
        rag = request.app.state.agent.rag
        if rag is None:
            raise HTTPException(409, "Corpus search requires live mode")
        return rag.search(body)

    @app.post("/api/v1/runs", response_model=RunResult)
    def run(body: RunRequest, request: Request):
        return request.app.state.agent.run(body)

    @app.get("/api/v1/threads/{thread_id}", response_model=RunResult)
    def inspect(
        thread_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")], request: Request
    ):
        result = request.app.state.agent.inspect(thread_id)
        if result is None:
            raise HTTPException(404, "Thread not found")
        return result

    @app.post("/api/v1/threads/{thread_id}/review", response_model=RunResult)
    def review(
        thread_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")],
        body: ReviewRequest,
        request: Request,
    ):
        try:
            return request.app.state.agent.resume(thread_id, body)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @app.get("/api/v1/briefs/{brief_id}", response_model=Brief)
    def brief(brief_id: Annotated[str, Path(pattern=r"^[a-f0-9]{32}$")], request: Request):
        result = request.app.state.agent.store.get(brief_id)
        if result is None:
            raise HTTPException(404, "Brief not found")
        return result

    return app


app = create_app()
