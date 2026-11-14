import time
from threading import Lock
from typing import Annotated, Literal
from uuid import uuid4

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context
from pydantic import BaseModel, Field, StringConstraints

from deep_agent_lab.agent import CITATION, SAVED_BRIEF, Markdown, Title, build_agent
from deep_agent_lab.knowledge import Evidence, Query
from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.settings import Settings
from deep_agent_lab.storage import BriefStore
from deep_agent_lab.tracing import Tracing

ThreadId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,80}$")]


class RunRequest(BaseModel):
    prompt: Query
    thread_id: ThreadId = Field(default_factory=lambda: uuid4().hex)


class Decision(BaseModel):
    type: Literal["approve", "reject", "edit"]
    title: Title | None = None
    markdown: Markdown | None = None


class ReviewRequest(BaseModel):
    interrupt_id: str = Field(min_length=1, max_length=100)
    decisions: list[Decision] = Field(min_length=1, max_length=32)


class PendingReview(BaseModel):
    id: str
    action_requests: list[dict]
    review_configs: list[dict]


class RunResult(BaseModel):
    thread_id: str
    status: Literal["completed", "interrupted"]
    answer: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    unknown_citations: list[str] = Field(default_factory=list)
    reviews: list[PendingReview] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    todos: list[dict] = Field(default_factory=list)
    saved_brief_ids: list[str] = Field(default_factory=list)
    trace_id: str | None = None


class ThreadConflict(Exception):
    pass


class AgentService:
    """Single local process. SQLite retains each thread and any pending approval."""

    def __init__(self, settings: Settings, checkpointer, *, model=None):
        self.settings = settings
        self.store = BriefStore(settings.state_dir)
        self.tracing = Tracing(settings)
        self.rag = RagService(settings, self.tracing) if settings.deep_lab_mode == "live" else None
        self.agent = build_agent(
            settings,
            self.store,
            checkpointer,
            model=model,
            tracing=self.tracing,
            rag=self.rag,
        )
        self.locks = tuple(Lock() for _ in range(32))

    def close(self):
        try:
            if self.rag is not None:
                self.rag.close()
        finally:
            self.tracing.close()

    @staticmethod
    def config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}, "recursion_limit": 48}

    def run(self, request: RunRequest) -> RunResult:
        with self.locks[hash(request.thread_id) % len(self.locks)]:
            config = self.config(request.thread_id)
            if self.agent.get_state(config).interrupts:
                raise ThreadConflict("Resolve this thread's pending review before adding a prompt.")
            state_input = {"messages": [{"role": "user", "content": request.prompt}]}
            return self._invoke(request.thread_id, state_input, input_text=request.prompt)

    def resume(self, thread_id: str, request: ReviewRequest) -> RunResult:
        with self.locks[hash(thread_id) % len(self.locks)]:
            pending = self.agent.get_state(self.config(thread_id)).interrupts
            if len(pending) != 1 or pending[0].id != request.interrupt_id:
                raise ThreadConflict("This approval is missing, stale, or already resolved.")
            actions = pending[0].value["action_requests"]
            if len(actions) != len(request.decisions):
                raise ValueError("Provide one decision for each action in the pending review.")
            decisions = []
            for action, decision in zip(actions, request.decisions, strict=True):
                if decision.type == "edit":
                    if decision.title is None or decision.markdown is None:
                        raise ValueError("An edit requires a title and Markdown.")
                    decisions.append(
                        {
                            "type": "edit",
                            "edited_action": {
                                "name": action["name"],
                                "args": {"title": decision.title, "markdown": decision.markdown},
                            },
                        }
                    )
                elif decision.title is not None or decision.markdown is not None:
                    raise ValueError("Title and Markdown apply to edit decisions.")
                else:
                    decisions.append({"type": decision.type})
            return self._invoke(
                thread_id, Command(resume={pending[0].id: {"decisions": decisions}})
            )

    def inspect(self, thread_id: str) -> RunResult | None:
        snapshot = self.agent.get_state(self.config(thread_id))
        if not snapshot.values:
            return None
        return self._result(thread_id, snapshot)

    def _invoke(self, thread_id: str, state_input, input_text: str | None = None) -> RunResult:
        start = time.perf_counter()
        config = self.config(thread_id)
        with (
            tracing_context(enabled=False),
            self.tracing.span(
                "deep-lab.turn",
                input=input_text,
                metadata={"mode": self.settings.deep_lab_mode},
            ) as span,
        ):
            self.agent.invoke(state_input, config)
            result = self._result(thread_id, self.agent.get_state(config))
            result.trace_id = span.trace_id
            span.update(
                output=result.answer,
                metadata={
                    "status": result.status,
                    "evidence_count": len(result.evidence),
                    "duration_ms": round((time.perf_counter() - start) * 1000),
                },
            )
            return result

    @staticmethod
    def _result(thread_id: str, snapshot) -> RunResult:
        reviews = [PendingReview(id=item.id, **item.value) for item in snapshot.interrupts]
        messages = snapshot.values.get("messages", [])
        turn_start = next(
            (
                index
                for index in reversed(range(len(messages)))
                if isinstance(messages[index], HumanMessage)
            ),
            0,
        )
        turn = messages[turn_start:]
        saved = snapshot.values.get("saved_briefs", {})
        saved_ids = [
            saved[message.tool_call_id]
            for message in turn
            if isinstance(message, ToolMessage) and message.tool_call_id in saved
        ]
        if not saved_ids and not saved:
            # Read results written before the save tool recorded structured state.
            saved_ids = [
                match[1]
                for message in turn
                if isinstance(message, ToolMessage) and message.name == "save_brief"
                if (match := SAVED_BRIEF.fullmatch(message.text))
            ]
        answer = messages[-1].text if messages and isinstance(messages[-1], AIMessage) else ""
        evidence = snapshot.values.get("evidence", {})
        if reviews:
            answer = ""
        ids = set(CITATION.findall(answer))
        return RunResult(
            thread_id=thread_id,
            status="interrupted" if reviews else "completed",
            answer=answer,
            reviews=reviews,
            todos=snapshot.values.get("todos", []),
            saved_brief_ids=saved_ids,
            unknown_citations=sorted(ids - evidence.keys()),
            evidence=[Evidence.model_validate(row) for row in evidence.values()],
            steps=[
                call["name"]
                for msg in messages
                if isinstance(msg, AIMessage)
                for call in msg.tool_calls
            ],
        )


def open_checkpointer(settings: Settings):
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(settings.state_dir / "checkpoints.sqlite"))
