"""Transparent ranking experiments. Production search remains rag/pipeline.py."""

import math
import re
from collections import Counter
from collections.abc import Callable

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


def adaptive_search(query: str, search: Callable, reformulate: Callable, *, max_queries=2):
    """Stop on a result, repeated query, or budget exhaustion. Failure is not an empty hit."""
    if not 1 <= max_queries <= 5:
        raise ValueError("Invalid query budget")
    queries = []
    for _ in range(max_queries):
        normalized = " ".join(query.lower().split())
        if not normalized or normalized in queries:
            break
        queries.append(normalized)
        hits = search(query)
        if hits:
            return hits, queries
        query = reformulate(query)
    return [], queries
