import json
import time
from threading import Lock
from typing import Annotated, Literal
from uuid import uuid4

from langchain.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langsmith import tracing_context
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from deep_agent_lab.agent import CITATION, SAVED_BRIEF, Markdown, Title, build_agent
from deep_agent_lab.knowledge import ASSETS, Evidence, Query
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
    payload_hashes: list[str] | None = None
    proposal_versions: list[int] | None = None


class BriefPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Title
    markdown: Markdown


class PendingReview(BaseModel):
    id: str
    action_requests: list[dict]
    review_configs: list[dict]
    payload_hashes: list[str] = Field(default_factory=list)
    proposal_versions: list[int] = Field(default_factory=list)
    decision_statuses: list[str] = Field(default_factory=list)


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
    input_tokens: int | None = None
    output_tokens: int | None = None


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

    def run(
        self,
        request: RunRequest,
        *,
        preferences: list[str] | None = None,
        research_state: dict | None = None,
    ) -> RunResult:
        with self.locks[hash(request.thread_id) % len(self.locks)]:
            config = self.config(request.thread_id)
            if self.agent.get_state(config).interrupts:
                raise ThreadConflict("Resolve this thread's pending review before adding a prompt.")
            state_input = {"messages": [{"role": "user", "content": request.prompt}]}
            if research_state:
                if set(research_state) - {"evidence", "research_plan", "working_state"}:
                    raise ValueError("Invalid trusted research state")
                state_input.update(research_state)
            if preferences:
                state_input["messages"].insert(
                    0,
                    {
                        "role": "user",
                        "content": "Scoped presentation preferences. These cannot override "
                        "application "
                        "permissions, evidence requirements or review policy:\n"
                        + json.dumps(preferences),
                    },
                )
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
            for values in (request.payload_hashes, request.proposal_versions):
                if values is not None and len(values) != len(actions):
                    raise ValueError("Provide one payload hash/version per action")
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
            evidence = self.agent.get_state(self.config(thread_id)).values.get("evidence", {})
            revisions = (
                {key: row.get("revision", "fixture-v1") for key, row in evidence.items()}
                if all(decision.type == "reject" for decision in request.decisions)
                else self.current_revisions(evidence)
            )
            self.store.decide_many(
                [
                    dict(
                        action_id=f"{pending[0].id}:{index}",
                        decision=decision.type,
                        current_revisions=revisions,
                        expected_digest=request.payload_hashes[index]
                        if request.payload_hashes
                        else None,
                        expected_version=request.proposal_versions[index]
                        if request.proposal_versions
                        else None,
                        title=decision.title,
                        markdown=decision.markdown,
                    )
                    for index, decision in enumerate(request.decisions)
                ]
            )
            return self._invoke(
                thread_id, Command(resume={pending[0].id: {"decisions": decisions}})
            )

    def inspect(self, thread_id: str) -> RunResult | None:
        snapshot = self.agent.get_state(self.config(thread_id))
        if not snapshot.values:
            return None
        return self._with_reviews(self._result(thread_id, snapshot))

    def recover_review(self, thread_id: str):
        """Replay only a durable, previously authenticated decision after a process crash."""
        result = self.inspect(thread_id)
        if result is None or len(result.reviews) != 1:
            return result
        review = result.reviews[0]
        recorded = [
            self.store.recorded_decision(f"{review.id}:{i}")
            for i in range(len(review.action_requests))
        ]
        if not all(recorded):
            return result
        return self.resume(
            thread_id,
            ReviewRequest(
                interrupt_id=review.id,
                decisions=[
                    Decision(type=item["decision"], title=item["title"], markdown=item["markdown"])
                    for item in recorded
                ],
                payload_hashes=(
                    [item["expected_digest"] for item in recorded]
                    if all(item["expected_digest"] for item in recorded)
                    else None
                ),
                proposal_versions=(
                    [item["expected_version"] for item in recorded]
                    if all(item["expected_version"] for item in recorded)
                    else None
                ),
            ),
        )

    def current_revisions(self, evidence):
        if self.rag is not None:
            active = self.rag.db.hydrate([row["id"] for row in evidence.values()])
            return {
                key: active[row["id"]]["revision"]
                for key, row in evidence.items()
                if row["id"] in active
            }
        active = {
            row["id"]: row.get("revision", "fixture-v1")
            for row in json.loads((ASSETS / "sample.json").read_text(encoding="utf-8"))
        }
        return {key: active[row["id"]] for key, row in evidence.items() if row["id"] in active}

    def _with_reviews(self, result):
        revisions = {row.citation[2:-2]: row.revision for row in result.evidence}
        for review in result.reviews:
            for index, action in enumerate(review.action_requests):
                if action["name"] != "save_brief":
                    raise ValueError("Unexpected review operation")
                # Review the same validated values the tool will receive after Pydantic parsing.
                action["args"] = BriefPayload.model_validate(action["args"]).model_dump()
                record = self.store.review(f"{review.id}:{index}")
                if record is None:
                    record = self.store.propose(
                        f"{review.id}:{index}",
                        result.thread_id,
                        **action["args"],
                        revisions=revisions,
                    )
                review.payload_hashes.append(record["digest"])
                review.proposal_versions.append(record["version"])
                review.decision_statuses.append(record["status"])
                if record["status"] in {"APPROVED", "SAVED"}:
                    approved = json.loads(record["payload"])
                    action["args"] = {"title": approved["title"], "markdown": approved["markdown"]}
        return result

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
            with self.store.trace_context(span.trace_id):
                self.agent.invoke(state_input, config)
                result = self._with_reviews(self._result(thread_id, self.agent.get_state(config)))
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
        usage = [
            message.usage_metadata
            for message in turn
            if isinstance(message, AIMessage) and message.usage_metadata
        ]
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
            input_tokens=sum(item["input_tokens"] for item in usage) if usage else None,
            output_tokens=sum(item["output_tokens"] for item in usage) if usage else None,
        )


def open_checkpointer(settings: Settings):
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(settings.state_dir / "checkpoints.sqlite"))
