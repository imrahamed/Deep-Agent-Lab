"""Deterministic doubles restricted to automated unit tests."""

import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from deep_agent_lab.knowledge import Evidence

ASSETS = Path(__file__).parent / "data"


class DemoModel(BaseChatModel):
    """Replay an inspectable tool-call sequence for the sample corpus."""

    profile: dict = {"max_input_tokens": 16_384, "tool_calling": True}

    @property
    def _llm_type(self) -> str:
        return "deep-lab-demo"

    def bind_tools(self, tools, **kwargs):
        names = tuple(tool.name for tool in tools)
        return self.bind(tool_names=names, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        names = kwargs.get("tool_names", ())
        response = self.respond(messages, names)
        return ChatResult(generations=[ChatGeneration(message=response)])

    @staticmethod
    def respond(messages, names) -> AIMessage:
        if not names:
            return AIMessage(content="Demo summary: consult the retained evidence and gaps.")
        turns = [i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)]
        if not turns:
            return AIMessage(content="Ask a question about the sample corpus.")
        question = messages[turns[-1]].text
        lower = question.lower()
        results = {
            msg.name: msg for msg in messages[turns[-1] + 1 :] if isinstance(msg, ToolMessage)
        }

        def call(name: str, **args) -> AIMessage:
            return AIMessage(
                content="",
                tool_calls=[{"name": name, "args": args, "id": f"demo-{len(messages)}-{name}"}],
            )

        if "save_brief" in results:
            result = results["save_brief"]
            status = re.search(r"Saved brief ([a-f0-9]{32})", result.text)
            markdown = next(
                call_data["args"]["markdown"]
                for message in reversed(messages)
                if isinstance(message, AIMessage)
                for call_data in message.tool_calls
                if call_data["name"] == "save_brief" and call_data["id"] == result.tool_call_id
            )
            if status:
                return AIMessage(content=f"Saved brief as {status[1]}.\n\n{markdown}")
            return AIMessage(content="The brief was not saved.")

        is_brief = "brief" in lower and "save_brief" in names
        if is_brief and "write_todos" in names and "write_todos" not in results:
            return call(
                "write_todos",
                todos=[
                    {"content": "Find evidence in the corpus", "status": "in_progress"},
                    {"content": "Write the brief and identify gaps", "status": "pending"},
                ],
            )
        if is_brief and "read_file" in names and "read_file" not in results:
            return call("read_file", file_path="/reference/skills/evidence-brief/SKILL.md")
        searches = [
            msg
            for msg in messages[turns[-1] + 1 :]
            if isinstance(msg, ToolMessage) and msg.name == "search_knowledge"
        ]
        # A deterministic policy for the fixture curriculum, NOT a substitute for live reasoning.
        multi = any(word in lower for word in ("compare", "readiness", "joint", "automatically"))
        queries = [question[:4000]]
        if multi:
            queries = ["production restore approval", "SEV-1 incident commander"]
            if "access" in lower or "readiness" in lower:
                queries.append("temporary elevated privileges application access")
            queries.append("joint authority automatic role transfer")
        if len(searches) < len(queries):
            return call("search_knowledge", query=queries[len(searches)], top_k=3)
        evidence_by_id = {}
        for result in searches:
            try:
                rows = json.loads(result.text)
                if isinstance(rows, list):
                    evidence_by_id.update({row["id"]: row for row in rows})
            except (ValueError, TypeError):
                return AIMessage(
                    content="Retrieval unavailable; policy absence has not been established."
                )
        evidence = list(evidence_by_id.values())

        if "delegate" in lower and "task" in names and "task" not in results:
            return call(
                "task",
                description=f"Review the corpus for: {question[:1800]}",
                subagent_type="policy-researcher",
            )

        if evidence:
            bullets = "\n".join(f"- {row['excerpt']} {row['citation']}" for row in evidence)
            answer = f"## Findings\n\n{bullets}\n\n## Next steps\n\nVerify the source excerpts."
        else:
            answer = "Evidence gap: the sample corpus contains no matching passage."
        if multi:
            answer += (
                "\n\n## Evidence gaps\n\nEvidence gap: the supplied passages do not "
                "establish joint authority or automatic role transfer. Request the "
                "cross-functional recovery procedure from the policy owner."
            )
        if is_brief and "write_todos" in results and "completed" not in results["write_todos"].text:
            return call(
                "write_todos",
                todos=[
                    {"content": "Find evidence in the corpus", "status": "completed"},
                    {"content": "Write the brief and identify gaps", "status": "completed"},
                ],
            )
        if is_brief and "save" in lower and evidence:
            return call("save_brief", title="Northstar evidence brief", markdown=answer)
        return AIMessage(content=answer)


def fixture_search(query: str, top_k: int) -> list[Evidence]:
    rows = [
        Evidence.model_validate(row)
        for row in json.loads((ASSETS / "sample.json").read_text(encoding="utf-8"))
    ]
    stop_words = {"the", "and", "for", "what", "who", "how", "which", "with", "does", "when"}
    terms = set(re.findall(r"[a-z]{3,}", query.lower())) - stop_words
    scored = [
        (len(terms & set(re.findall(r"[a-z]{3,}", row.excerpt.lower()))), row) for row in rows
    ]
    result = [row for score, row in sorted(scored, key=lambda item: -item[0]) if score][:top_k]
    for row in result:
        row.source = "file:///test/" + row.source.rsplit("/", 1)[-1] + ".md"
    return result


def install_runtime(monkeypatch=None):
    import deep_agent_lab.agent as agent
    import deep_agent_lab.capstone as capstone
    import deep_agent_lab.service as service

    def retrieve(settings, query, mode="hybrid", top_k=4, **kwargs):
        return fixture_search(query, top_k)

    class TestRag:
        def __init__(self, *args, **kwargs):
            rows = fixture_search("restore incident access recovery", 5)
            self.db = SimpleNamespace(
                hydrate=lambda ids: {
                    row.id: {**row.model_dump(), "content": row.excerpt}
                    for row in rows
                    if row.id in ids
                }
            )

        def health(self):
            return {"status": "ok"}

        def close(self):
            pass

    replacements = [
        (agent, "local_model", lambda settings: DemoModel()),
        (agent, "search_knowledge", retrieve),
        (service, "RagService", TestRag),
        (capstone, "search_knowledge", retrieve),
    ]
    for target, name, value in replacements:
        if monkeypatch is None:
            setattr(target, name, value)
        else:
            monkeypatch.setattr(target, name, value)
