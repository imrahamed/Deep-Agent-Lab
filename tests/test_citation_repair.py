from types import SimpleNamespace

from langchain.agents.middleware.types import ModelResponse
from langchain.messages import AIMessage, HumanMessage, ToolMessage

from deep_agent_lab.instrumentation import ResearchMiddleware
from deep_agent_lab.knowledge import fixture_search
from deep_agent_lab.model import DemoModel
from deep_agent_lab.tracing import Tracing


def test_citation_repair_has_one_targeted_attempt_and_disables_tools():
    row = fixture_search("restore", 1)[0]
    requests = []
    request = SimpleNamespace(
        model=DemoModel(),
        messages=[
            HumanMessage("approver?"),
            ToolMessage(content="evidence", name="search_knowledge", tool_call_id="search-1"),
        ],
        state={"evidence": {row.citation[2:-2]: row.model_dump()}},
    )
    request.override = lambda **updates: SimpleNamespace(model=request.model, **updates)

    def handler(current):
        requests.append(current)
        text = "Uncited draft" if len(requests) == 1 else "Repaired answer " + row.citation
        return ModelResponse(result=[AIMessage(content=text)])

    result = ResearchMiddleware(Tracing(), repair_citations=True).wrap_model_call(request, handler)
    assert row.citation in result.result[-1].text
    assert len(requests) == 2 and requests[1].tools == []
    assert "Copy the exact citation" in requests[1].messages[-1].text
