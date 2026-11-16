"""A deliberately small model/tool loop. The real runtime lives in agent.py."""

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    top_k: int = Field(default=3, ge=1, le=5)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class FinalAnswer:
    text: str


class StepLimit(RuntimeError):
    pass


def agent_loop(decide: Callable, search: Callable, question: str, *, max_steps: int = 4):
    """Return the answer AND observable trajectory; invalid calls never reach search."""
    if max_steps < 1 or not question.strip():
        raise ValueError("A question and positive step budget are required")
    messages = [{"role": "user", "content": question}]
    seen = set()
    for _ in range(max_steps):
        action = decide(messages)
        if isinstance(action, FinalAnswer):
            messages.append({"role": "assistant", "content": action.text})
            return action.text, messages
        if not isinstance(action, ToolCall) or action.name != "search_knowledge":
            raise ValueError("Unsupported action")
        if not action.id or action.id in seen:
            raise ValueError("Tool call IDs must be nonempty and unique")
        arguments = SearchArgs.model_validate(action.arguments)
        seen.add(action.id)
        messages.append({"role": "assistant", "tool_call_id": action.id, "name": action.name})
        rows = search(arguments.query, arguments.top_k)
        messages.append({"role": "tool", "tool_call_id": action.id, "content": json.dumps(rows)})
    raise StepLimit(f"Model did not finish within {max_steps} decisions")
