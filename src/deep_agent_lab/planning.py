"""Dependency-aware research plans and process-local specialist scheduling."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class PlanTask:
    id: str
    description: str
    dependencies: set[str] = field(default_factory=set)
    status: str = "pending"
    evidence_ids: set[str] = field(default_factory=set)


def validate_plan(tasks: dict[str, PlanTask]):
    visited, visiting = set(), set()

    def visit(key):
        if key not in tasks or tasks[key].id != key:
            raise ValueError("Unknown dependency or inconsistent task ID")
        if key in visiting:
            raise ValueError("Dependency cycle")
        if key not in visited:
            visiting.add(key)
            for dependency in tasks[key].dependencies:
                visit(dependency)
            visiting.remove(key)
            visited.add(key)

    for key in tasks:
        visit(key)


def ready_tasks(tasks: dict[str, PlanTask]) -> list[PlanTask]:
    validate_plan(tasks)
    return [
        task
        for task in tasks.values()
        if task.status == "pending"
        and all(tasks[key].status == "verified" for key in task.dependencies)
    ]


def complete_task(tasks: dict[str, PlanTask], key: str, evidence: set[str], registry: set[str]):
    if tasks[key] not in ready_tasks(tasks) or not evidence or evidence - registry:
        raise ValueError("Task has unmet dependencies or unverified evidence")
    tasks[key].evidence_ids = set(evidence)
    tasks[key].status = "verified"


class SpecialistFinding(BaseModel):
    question: str
    claim: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    quotes: list[str] = Field(default_factory=list)
    revisions: list[str] = Field(default_factory=list)
    status: Literal["proposed", "supported", "insufficient", "contradictory", "failed"]
    unresolved: list[str] = Field(default_factory=list)


def verify_handoff(finding: SpecialistFinding, registry):
    """Independently verify a child's references; never trust its self-reported label."""
    from deep_agent_lab.evidence import Claim, Reference, Verdict, extractive_verdict

    if (
        not finding.claim
        or not finding.evidence_ids
        or len(finding.evidence_ids) != len(finding.quotes)
        or len(finding.quotes) != len(finding.revisions)
    ):
        return Verdict(label="insufficient", reason="Incomplete handoff", method="handoff")
    claim = Claim(
        text=finding.claim,
        references=[
            Reference(evidence_id=key, revision=revision, quote=quote)
            for key, quote, revision in zip(
                finding.evidence_ids, finding.quotes, finding.revisions, strict=True
            )
        ],
    )
    return extractive_verdict(claim, registry)


async def run_specialists(
    topics: list[str], research: Callable, *, concurrency=2, timeout=1.0, deadline=5.0, max_tasks=8
):
    """One total deadline includes queue time; child failures preserve sibling results."""
    if (
        not 1 <= concurrency <= 8
        or not 0 < timeout <= deadline
        or len(topics) > max_tasks
        or len(set(topics)) != len(topics)
    ):
        raise ValueError("Invalid specialist budget")
    semaphore = asyncio.Semaphore(concurrency)
    results = {}

    async def one(topic):
        async with semaphore:
            try:
                async with asyncio.timeout(timeout):
                    results[topic] = {"status": "success", "result": await research(topic)}
            except TimeoutError:
                results[topic] = {"status": "timeout"}
            except Exception as error:
                results[topic] = {"status": "failed", "error_type": type(error).__name__}

    children = [asyncio.create_task(one(topic)) for topic in topics]
    try:
        async with asyncio.timeout(deadline):
            await asyncio.gather(*children)
    except TimeoutError:
        for topic in topics:
            results.setdefault(topic, {"status": "deadline"})
    finally:
        for child in children:
            child.cancel()
        await asyncio.gather(*children, return_exceptions=True)
    return results
