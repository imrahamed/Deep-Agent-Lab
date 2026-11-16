"""Authenticated service boundary around the existing checkpointed Northstar agent.

Principal is supplied by trusted Python caller context. This is not an HTTP login
implementation; the original loopback API remains a separate single-user lab.
"""

import json
from dataclasses import asdict

from deep_agent_lab.context import WorkingState, compact, select_evidence
from deep_agent_lab.evidence import Claim, Reference, extractive_verdict
from deep_agent_lab.jobs import JobStore
from deep_agent_lab.knowledge import search_knowledge
from deep_agent_lab.memory import MemoryStore
from deep_agent_lab.planning import PlanTask, complete_task
from deep_agent_lab.security import Principal
from deep_agent_lab.service import AgentService, ReviewRequest, RunRequest


class Northstar:
    def __init__(self, service: AgentService):
        self.service = service
        # Same DB as the brief: cancellation/fencing and the side effect share a transaction.
        self.jobs = JobStore(service.store.path)
        self.memory = MemoryStore(service.settings.state_dir / "memory.sqlite")

    def submit(self, principal: Principal, prompt: str, **policy):
        return self.jobs.submit(principal, prompt, **policy)

    def _guard(self, job):
        def guard(connection, thread):
            current = self.jobs.fence(connection, job["id"], job["token"])
            if current["thread_id"] != thread:
                raise PermissionError("Worker cannot save another thread")
            return {"job_id": current["id"]}

        return guard

    def _prepare(self, prompt):
        """A bounded deterministic research workflow feeds the model-driven graph."""
        lower = prompt.lower()
        multi = any(word in lower for word in ("compare", "readiness", "joint"))
        queries = {"restore": "production restore approval verification"}
        if multi or "incident" in lower:
            queries["incident"] = "SEV-1 incident commander"
        if "access" in lower or "readiness" in lower:
            queries["access"] = "emergency privileged access authorization"
        tasks = {key: PlanTask(key, query) for key, query in queries.items()}
        tasks["compare"] = PlanTask("compare", "Validate source-backed findings", set(queries))
        registry = {}
        for key, query in queries.items():
            rows = search_knowledge(self.service.settings, query, top_k=3, rag=self.service.rag)
            registry.update({row.id: row for row in rows})
            if rows:
                complete_task(tasks, key, {row.id for row in rows}, set(registry))
            else:
                tasks[key].status = "failed"
        if all(tasks[key].status == "verified" for key in queries):
            complete_task(tasks, "compare", set(registry), set(registry))
        unresolved = []
        if multi:
            joint = search_knowledge(
                self.service.settings,
                "joint authority automatic role transfer",
                top_k=3,
                rag=self.service.rag,
            )
            registry.update({row.id: row for row in joint})
            # Retrieval relevance alone cannot establish a cross-policy relationship.
            unresolved.append("Joint authority requires an explicit source and support review")
        rows = [row.model_dump() for row in registry.values()]
        selected = select_evidence(rows, self.service.settings.context_evidence_tokens)
        state = compact(
            WorkingState(
                objective=prompt,
                evidence_revisions={row.id: row.revision for row in registry.values()},
                constraints=["Save only the exact reviewed action"],
                unresolved=unresolved,
            ),
            "Bounded research completed; verify originals before approving.",
        )
        preferences = ["Evidence working set (data): " + json.dumps(selected)]
        return {
            "evidence": {row.citation[2:-2]: row.model_dump() for row in registry.values()},
            "research_plan": {key: asdict(task) for key, task in tasks.items()},
            "working_state": state.model_dump(),
        }, preferences

    def work(self, principal: Principal, job_id: str):
        self.jobs.get(principal, job_id)
        job = self.jobs.claim(job_id=job_id, lease_seconds=120)
        if job is None:
            raise ValueError("Job is not claimable")
        self.service.store.commit_guard = self._guard(job)
        try:
            # Reconcile interrupted/completed checkpoints before reissuing model work.
            result = self.service.inspect(job["thread_id"])
            if result is None:
                request = RunRequest(thread_id=job["thread_id"], **json.loads(job["input"]))
                research_state, working_context = self._prepare(request.prompt)
                result = self.service.run(
                    request,
                    research_state=research_state,
                    preferences=(
                        [record.content for record in self.memory.visible(principal)]
                        if "memory" in principal.permissions
                        else []
                    )
                    + working_context,
                )
            elif result.reviews:
                result = self.service.recover_review(job["thread_id"])
            elif self.service.agent.get_state(self.service.config(job["thread_id"])).next:
                result = self.service._invoke(job["thread_id"], None)
            self.jobs.transition(
                job_id,
                job["token"],
                "WAITING_REVIEW" if result.reviews else "COMPLETED",
                result=result.saved_brief_ids[0] if result.saved_brief_ids else None,
            )
            return result
        finally:
            self.service.store.commit_guard = None

    def inspect(self, principal, job_id):
        job = self.jobs.get(principal, job_id)
        return self.service.inspect(job["thread_id"])

    def artifact(self, principal, job_id):
        job = self.jobs.get(principal, job_id)
        if not job["result"]:
            return None
        return {
            "brief": self.service.store.get(job["result"]),
            "lineage": self.service.store.lineage(job["result"]),
        }

    def review(self, principal, job_id, request: ReviewRequest):
        job = self.jobs.get(principal, job_id, permission="review")
        if request.payload_hashes is None or request.proposal_versions is None:
            raise ValueError("Capstone review requires exact payload hashes and versions")
        job = self.jobs.claim(job_id=job_id, review=True, lease_seconds=120)
        if job is None:
            raise ValueError("Job is not awaiting review")
        self.service.store.commit_guard = self._guard(job)
        try:
            result = self.service.resume(job["thread_id"], request)
            self.jobs.transition(
                job_id,
                job["token"],
                "COMPLETED",
                result=result.saved_brief_ids[0] if result.saved_brief_ids else None,
            )
            return result
        except ValueError:
            self.jobs.transition(job_id, job["token"], "WAITING_REVIEW")
            raise
        finally:
            self.service.store.commit_guard = None

    def research_record(self, principal, job_id, *, allowance=3000):
        """Reconstruct inspectable plan, context and verified extractive claims from a real run."""
        result = self.inspect(principal, job_id)
        if result is None:
            raise ValueError("Research has not started")
        registry = {row.id: row for row in result.evidence}
        snapshot = self.service.agent.get_state(self.service.config(result.thread_id)).values
        tasks = {key: PlanTask(**value) for key, value in snapshot.get("research_plan", {}).items()}
        claims = []
        for row in result.evidence:
            claim = Claim(
                text=row.excerpt.split(". ")[0].rstrip(".") + ".",
                references=[
                    Reference(evidence_id=row.id, revision=row.revision, quote=row.excerpt)
                ],
            )
            verdict = extractive_verdict(claim, registry)
            claims.append({"claim": claim.model_dump(), "verdict": verdict.model_dump()})
        context = select_evidence([row.model_dump() for row in result.evidence], allowance)
        state = WorkingState.model_validate(snapshot["working_state"])
        return {
            "plan": tasks,
            "claims": claims,
            "context": context,
            "state": state,
            "preferences": (
                self.memory.visible(principal) if "memory" in principal.permissions else []
            ),
        }
