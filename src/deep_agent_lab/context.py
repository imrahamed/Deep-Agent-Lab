"""Context selection and compaction with explicit preservation invariants."""

import hashlib
import json
from dataclasses import dataclass

from pydantic import BaseModel, Field


def approximate_tokens(text: str) -> int:
    """Teaching estimate only. Never present this as provider-reported usage."""
    return (len(text.encode("utf-8")) + 3) // 4


@dataclass(frozen=True)
class ContextBudget:
    window: int = 16384
    instructions: int = 2000
    history: int = 2000
    output: int = 1536
    headroom: int = 1000

    @property
    def evidence_allowance(self):
        values = (self.window, self.instructions, self.history, self.output, self.headroom)
        if any(value < 0 for value in values) or self.window == 0:
            raise ValueError("Invalid context allocation")
        return max(0, self.window - sum(values[1:]))


def select_evidence(rows: list[dict], allowance: int, required: frozenset[str] = frozenset()):
    registry = {row["id"]: row for row in rows}
    if allowance < 0 or len(registry) != len(rows) or required - registry.keys():
        raise ValueError("Invalid budget, duplicate IDs or missing required evidence")

    def cost(row):
        return approximate_tokens(json.dumps(row, sort_keys=True))

    chosen = [row for row in rows if row["id"] in required]
    remaining = allowance - sum(cost(row) for row in chosen)
    if remaining < 0:
        raise ValueError("Required evidence exceeds budget; offload or increase allowance")
    for row in sorted(rows, key=lambda row: (-row.get("relevance", 0), row["id"])):
        if row["id"] not in required and cost(row) <= remaining:
            chosen.append(row)
            remaining -= cost(row)
    return chosen


class WorkingState(BaseModel):
    objective: str
    evidence_revisions: dict[str, str] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    summary: str = ""


def compact(state: WorkingState, summary: str) -> WorkingState:
    """Only narrative is lossy; copy durable constraints and evidence handles verbatim."""
    return state.model_copy(update={"summary": summary}, deep=True)


def context_payload(evidence: list[dict], state: WorkingState) -> str:
    """Deterministic payload including both evidence and working state/history."""
    return json.dumps(
        {"evidence": evidence, "working_state": state.model_dump()},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )


def validate_compaction(before: WorkingState, after: WorkingState):
    if before.model_dump(exclude={"summary"}) != after.model_dump(exclude={"summary"}):
        raise ValueError("Compaction lost required state")


def trim_turns(turns: list[list[dict]], token_budget: int) -> list[list[dict]]:
    """Keep whole newest turns so an assistant call cannot lose its tool result."""
    if token_budget < 0:
        raise ValueError("Negative token budget")
    kept = []
    for turn in reversed(turns):
        cost = approximate_tokens(json.dumps(turn))
        if cost > token_budget:
            break
        kept.insert(0, turn)
        token_budget -= cost
    return kept


def prefix_key(instructions: str, tool_schema: dict) -> str:
    """Fingerprint an unchanged prefix, NOT an implementation of provider KV caching."""
    return hashlib.sha256(
        (instructions + json.dumps(tool_schema, sort_keys=True)).encode()
    ).hexdigest()
