import json
from threading import Lock

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ExtendedModelResponse, ModelResponse
from langchain.messages import HumanMessage, ToolMessage
from langchain_core.callbacks import BaseCallbackHandler

from deep_agent_lab.tracing import Tracing


class ExecutionMetrics(BaseCallbackHandler):
    """Count actual parent/child calls, failures, reported usage and repeated queries."""

    def __init__(self):
        self.lock = Lock()
        self.started = 0
        self.failed = 0
        self.models = []
        self.tools = []

    def on_chat_model_start(self, serialized, messages, **kwargs):
        with self.lock:
            self.started += 1

    def on_llm_error(self, error, **kwargs):
        with self.lock:
            self.failed += 1

    def on_llm_end(self, response, **kwargs):
        with self.lock:
            for generations in response.generations:
                for generation in generations:
                    message = getattr(generation, "message", None)
                    self.models.append(getattr(message, "usage_metadata", None))

    def on_tool_start(self, serialized, input_str, **kwargs):
        with self.lock:
            self.tools.append({"name": serialized.get("name"), "input": input_str})

    def report(self):
        with self.lock:
            searches = []
            for item in self.tools:
                if item["name"] == "search_knowledge":
                    try:
                        query = json.loads(item["input"])["query"]
                    except (ValueError, KeyError, TypeError):
                        query = item["input"]
                    searches.append(" ".join(query.casefold().split()))
            complete = bool(self.models) and len(self.models) == self.started and all(self.models)
            return {
                "model_calls": self.started,
                "completed_model_calls": len(self.models),
                "failed_model_calls": self.failed,
                "tool_calls": len(self.tools),
                "duplicated_retrieval": len(searches) - len(set(searches)),
                "duplicate_retrieval_basis": "normalized_query",
                "input_tokens": sum(row["input_tokens"] for row in self.models)
                if complete
                else None,
                "output_tokens": sum(row["output_tokens"] for row in self.models)
                if complete
                else None,
                "usage_complete": complete,
            }


class ResearchMiddleware(AgentMiddleware):
    """Trace model turns and give a live model one chance to repair uncited answers."""

    def __init__(self, tracing: Tracing, repair_citations: bool):
        self.tracing = tracing
        self.repair_citations = repair_citations

    def wrap_model_call(self, request, handler) -> ExtendedModelResponse:
        def call(model_request):
            with self.tracing.span(
                "deep-lab.model",
                as_type="generation",
                model=getattr(model_request.model, "model", "unknown"),
                metadata={"message_count": len(model_request.messages)},
                input=[message.text for message in model_request.messages]
                if self.tracing.capture_content
                else None,
            ) as span:
                response = handler(model_request)
                if isinstance(response, ModelResponse) and response.result:
                    reply = response.result[-1]
                    usage = reply.usage_metadata or {}
                    details = {
                        kind: usage[f"{kind}_tokens"]
                        for kind in ("input", "output", "total")
                        if f"{kind}_tokens" in usage
                    }
                    span.update(output=reply.text, usage_details=details or None)
                return response

        response = call(request)
        if not self.repair_citations or not isinstance(response, ModelResponse):
            return response
        reply = response.result[-1]
        if not reply.text or reply.tool_calls:
            return response
        current_turn = []
        for message in reversed(request.messages):
            if isinstance(message, HumanMessage):
                break
            current_turn.append(message)
        if any(isinstance(msg, ToolMessage) and msg.name == "save_brief" for msg in current_turn):
            return response
        if not any(
            isinstance(msg, ToolMessage) and msg.name == "search_knowledge" for msg in current_turn
        ):
            return response
        evidence = request.state.get("evidence", {})
        if not evidence or "evidence gap" in reply.text.lower():
            return response
        if any(row["citation"] in reply.text for row in evidence.values()):
            return response
        reminder = HumanMessage(
            "Revise the draft answer below. Copy the exact citation string from the "
            "matching search tool result beside each factual claim. A citation is the "
            "bracketed token in the citation field. Return only the revised answer. "
            "Use plain text, without calling tools.\n\n" + reply.text,
        )
        repaired = call(request.override(messages=[*request.messages, reminder], tools=[]))
        if isinstance(repaired, ModelResponse) and repaired.result[-1].text:
            return repaired
        return response
