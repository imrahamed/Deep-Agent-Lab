import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_ollama import ChatOllama

from deep_agent_lab.settings import Settings


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
        if "search_knowledge" not in results:
            return call("search_knowledge", query=question[:4000], top_k=3)
        try:
            evidence = json.loads(results["search_knowledge"].text)
        except (ValueError, TypeError):
            evidence = []

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


def local_model(settings: Settings) -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_chat_model,
        base_url=str(settings.ollama_url).rstrip("/"),
        num_ctx=settings.ollama_context_tokens,
        num_predict=1536,
        temperature=0,
        reasoning=False,
        client_kwargs={"timeout": settings.request_timeout_seconds, "trust_env": False},
        profile={"max_input_tokens": settings.ollama_context_tokens, "tool_calling": True},
    )
