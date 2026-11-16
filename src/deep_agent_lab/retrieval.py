"""Transparent ranking experiments. Production search remains rag/pipeline.py."""

import math
import re
from collections import Counter
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from deep_agent_lab.knowledge import Evidence
from deep_agent_lab.rag.search import reciprocal_rank_fusion


def terms(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25(query: str, rows: list[Evidence], *, k1=1.2, b=0.75) -> list[dict]:
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("Invalid BM25 parameters")
    if not rows:
        return []
    docs = [Counter(terms(row.excerpt)) for row in rows]
    average = sum(sum(doc.values()) for doc in docs) / len(docs) or 1
    scores = []
    for row, doc in zip(rows, docs, strict=True):
        length = sum(doc.values())
        score = 0.0
        for term in set(terms(query)):
            df = sum(term in other for other in docs)
            idf = math.log(1 + (len(docs) - df + 0.5) / (df + 0.5))
            frequency = doc[term]
            score += idf * frequency * (k1 + 1) / (frequency + k1 * (1 - b + b * length / average))
        if score > 0:
            scores.append({"_id": row.id, "_score": score})
    return sorted(scores, key=lambda hit: (-hit["_score"], hit["_id"]))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b) or not all(math.isfinite(x) for x in [*a, *b]):
        raise ValueError("Vectors need matching dimensions and finite coordinates")
    denominator = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    if not denominator:
        raise ValueError("Zero vector")
    return sum(x * y for x, y in zip(a, b, strict=True)) / denominator


def vector_rank(query: list[float], vectors: dict[str, list[float]]) -> list[dict]:
    return sorted(
        [{"_id": key, "_score": cosine(query, vector)} for key, vector in vectors.items()],
        key=lambda hit: (-hit["_score"], hit["_id"]),
    )


def hybrid(keyword: list[dict], semantic: list[dict], *, k=60):
    return reciprocal_rank_fusion([keyword, semantic], k=k)


def rerank(query: str, candidates: list[Evidence], score: Callable, *, top_k=3):
    """Inject a relevance model or an explicitly labelled educational scorer."""
    if top_k < 1:
        raise ValueError("top_k must be positive")
    scored = [(score(query, row.excerpt), row) for row in candidates]
    if not all(math.isfinite(value) for value, _ in scored):
        raise ValueError("Reranker returned nonfinite scores")
    return [row for _, row in sorted(scored, key=lambda pair: (-pair[0], pair[1].id))][:top_k]


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    answerable: bool
    missing_information: list[str] = Field(default_factory=list)


class AdaptiveSearchTrace(BaseModel):
    original_question: str = Field(frozen=True)
    queries_attempted: list[str]
    retrieved_evidence: list[Evidence]
    missing_information: list[str]
    answerable: bool
    stop_reason: Literal[
        "answerable",
        "query_budget_exhausted",
        "repeated_query",
        "reformulation_drift",
        "no_new_query",
    ]


def protected_terms(question: str) -> set[str]:
    """A conservative rewrite guard, with no claim to semantic equivalence checking."""
    tokens = set(re.findall(r"[\w]+(?:-[\w]+)*", question.casefold()))
    scope = {
        "not",
        "no",
        "never",
        "without",
        "only",
        "except",
        "unless",
        "production",
        "staging",
        "development",
    }
    return {token for token in tokens if any(c.isdigit() for c in token)} | (tokens & scope)


def adaptive_search(
    original_question: str,
    search: Callable[[str], list[Evidence]],
    reformulate: Callable[[str, list[str], list[str]], str],
    assess: Callable[[str, list[Evidence]], EvidenceAssessment],
    *,
    max_queries: int = 2,
) -> AdaptiveSearchTrace:
    """Bound evidence gathering around an immutable question and an injected assessor.

    Infrastructure and assessor errors propagate. They never establish policy absence.
    Callbacks receive copies so their mutations cannot change accumulated trace state.
    """
    if type(max_queries) is not int or not 1 <= max_queries <= 5:
        raise ValueError("Invalid query budget")
    if not original_question.strip():
        raise ValueError("A nonempty original question is required")
    query = original_question
    queries: list[str] = []
    seen: set[str] = set()
    registry: dict[str, Evidence] = {}
    required = protected_terms(original_question)
    assessment = EvidenceAssessment(answerable=False, missing_information=[original_question])
    reason = "query_budget_exhausted"
    for _ in range(max_queries):
        normalized = " ".join(query.casefold().split())
        if not normalized:
            reason = "no_new_query"
            break
        if normalized in seen:
            reason = "repeated_query"
            break
        tokens = set(re.findall(r"[\w]+(?:-[\w]+)*", query.casefold()))
        if required - tokens:
            reason = "reformulation_drift"
            break
        seen.add(normalized)
        queries.append(query)
        for hit in search(query):
            row = Evidence.model_validate(hit)
            if row.id in registry and registry[row.id] != row:
                raise ValueError("Conflicting content or provenance for an evidence ID")
            registry.setdefault(row.id, row.model_copy(deep=True))
        assessment = EvidenceAssessment.model_validate(
            assess(original_question, [row.model_copy(deep=True) for row in registry.values()])
        )
        if assessment.answerable:
            if not registry:
                raise ValueError("An evidence-backed assessment requires evidence")
            reason = "answerable"
            break
        if not assessment.missing_information:
            raise ValueError("An unanswerable assessment must identify missing information")
        if len(queries) < max_queries:
            query = reformulate(
                original_question, queries.copy(), assessment.missing_information.copy()
            )
    return AdaptiveSearchTrace(
        original_question=original_question,
        queries_attempted=queries,
        retrieved_evidence=list(registry.values()),
        missing_information=assessment.missing_information,
        answerable=assessment.answerable,
        stop_reason=reason,
    )
