from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.errors import ModelProviderError
from app.models.schemas import SearchResult


def rerank_results(
    query: str,
    results: list[SearchResult],
    top_n: int,
    settings: Settings | None = None,
) -> list[SearchResult]:
    settings = settings or get_settings()
    if not _should_call_reranker(settings) or not results:
        return results[:top_n]

    candidates = results[: max(settings.reranker_candidate_limit, top_n)]
    documents = [result.content[: settings.reranker_max_chars] for result in candidates]
    payload = {
        "model": settings.reranker_model,
        "query": query,
        "documents": documents,
        "return_documents": False,
        "top_n": min(top_n, len(documents)),
    }
    url = f"{settings.openai_compatible_base_url.rstrip('/')}/rerank"

    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.openai_compatible_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=settings.reranker_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # pragma: no cover - external provider behavior varies.
        raise ModelProviderError(f"Reranker request failed: {exc}") from exc

    reranked: list[SearchResult] = []
    used_indexes: set[int] = set()
    for item in data.get("results", []):
        index = item.get("index")
        if not isinstance(index, int) or index < 0 or index >= len(candidates):
            continue
        used_indexes.add(index)
        result = candidates[index].model_copy(deep=True)
        rerank_score = item.get("relevance_score")
        if rerank_score is not None:
            result.score = float(rerank_score)
            result.metadata["rerank_score"] = float(rerank_score)
        result.metadata["reranker_model"] = settings.reranker_model
        result.metadata["ranker"] = "siliconflow_reranker"
        reranked.append(result)

    if len(reranked) < top_n:
        for index, result in enumerate(candidates):
            if index in used_indexes:
                continue
            fallback = result.model_copy(deep=True)
            fallback.metadata.setdefault("ranker", "hybrid_fallback")
            reranked.append(fallback)
            if len(reranked) >= top_n:
                break
    return reranked[:top_n]


def _should_call_reranker(settings: Settings) -> bool:
    return (
        settings.enable_reranker
        and settings.has_api_key
        and bool(settings.reranker_model.strip())
    )
