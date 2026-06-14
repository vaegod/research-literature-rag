from __future__ import annotations

import re

from app.config import Settings, get_settings
from app.errors import ModelProviderError
from app.models.schemas import SearchResult
from app.retriever.bm25 import bm25_search
from app.retriever.reranker import rerank_results
from app.retriever.vector_store import similarity_search

INTENT_SECTION_BOOSTS: dict[str, dict[str, float]] = {
    "contribution": {"abstract": 0.3, "introduction": 0.45, "conclusion": 0.25, "body": 0.08},
    "method": {"method": 0.45, "abstract": 0.18, "introduction": 0.18, "body": 0.08},
    "experiment": {"experiments": 0.5, "method": 0.12, "body": 0.05},
    "limitation": {"limitations": 0.45, "conclusion": 0.25, "body": 0.05},
    "summary": {"abstract": 0.3, "introduction": 0.25, "method": 0.16, "conclusion": 0.16},
}

INTENT_QUERY_TERMS: dict[str, str] = {
    "contribution": "abstract introduction main contribution contributions proposed novelty",
    "method": "method approach framework model proposed",
    "experiment": "experiment experimental setup results evaluation datasets metrics",
    "limitation": "limitation limitations discussion conclusion future work",
    "summary": "abstract introduction method experiment conclusion summary",
}

INTENT_KEYWORD_BOOSTS: dict[str, list[str]] = {
    "contribution": ["contribution", "contributions", "propose", "proposed", "novel", "main"],
    "method": ["method", "approach", "framework", "model", "rationale", "distillation"],
    "experiment": ["experiment", "results", "evaluation", "dataset", "accuracy", "performance"],
    "limitation": ["limitation", "limitations", "future work", "discussion"],
    "summary": ["abstract", "introduction", "conclusion", "proposed"],
}


def search_knowledge_base(
    query: str,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[SearchResult]:
    settings = settings or get_settings()
    top_k = top_k or settings.default_top_k
    intent = infer_retrieval_intent(query)
    enhanced_query = enhance_query_for_intent(query, intent)
    fetch_k = max(top_k * settings.retrieval_fetch_multiplier, settings.retrieval_min_candidates)

    dense_docs = similarity_search(query=enhanced_query, top_k=fetch_k, settings=settings)
    dense_docs = rerank_by_section_intent(dense_docs, query, intent)
    dense_results = _dense_results_from_docs(dense_docs)

    bm25_results = []
    if settings.retrieval_mode in {"hybrid", "bm25"}:
        bm25_results = bm25_search(enhanced_query, fetch_k, settings=settings)

    fused_results = fuse_retrieval_results(dense_results, bm25_results, settings)
    fused_results = rerank_search_results_by_section(fused_results, query, intent)
    try:
        return rerank_results(query, fused_results, top_k, settings=settings)
    except ModelProviderError as exc:
        fallback = fused_results[:top_k]
        for result in fallback:
            result.metadata["rerank_error"] = str(exc)
            result.metadata.setdefault("ranker", "hybrid_fallback")
        return fallback


def infer_retrieval_intent(query: str) -> str:
    lowered = query.lower()
    if _contains_any(lowered, ["主要贡献", "贡献", "创新点", "novelty", "contribution"]):
        return "contribution"
    if _contains_any(
        lowered,
        [
            "方法",
            "流程",
            "框架",
            "核心方法",
            "原理",
            "机制",
            "为什么能",
            "为什么可以",
            "method",
            "approach",
            "framework",
            "how does",
            "why can",
        ],
    ):
        return "method"
    if _contains_any(lowered, ["实验", "结果", "数据集", "指标", "experiment", "result", "dataset", "metric", "performance"]):
        return "experiment"
    if _contains_any(lowered, ["局限", "不足", "limitation", "future work", "discussion"]):
        return "limitation"
    if _contains_any(lowered, ["总结", "概括", "摘要", "summary", "abstract"]):
        return "summary"
    return "general"


def enhance_query_for_intent(query: str, intent: str) -> str:
    terms = INTENT_QUERY_TERMS.get(intent)
    if not terms:
        return query
    return f"{query}\n{terms}"


def rerank_by_section_intent(
    docs_with_scores: list[tuple[object, float]],
    query: str,
    intent: str,
) -> list[tuple[object, float]]:
    if intent == "general":
        return docs_with_scores

    section_boosts = INTENT_SECTION_BOOSTS.get(intent, {})
    keyword_boosts = INTENT_KEYWORD_BOOSTS.get(intent, [])
    query_sources = _mentioned_pdf_sources(query)

    candidates: list[tuple[object, float, bool]] = []
    for doc, score in docs_with_scores:
        metadata = dict(getattr(doc, "metadata", {}) or {})
        content = str(getattr(doc, "page_content", "")).lower()
        is_reference = metadata.get("section") == "references" or _looks_like_reference_text(content)
        candidates.append((doc, score, is_reference))

    if intent in {"contribution", "summary", "method", "experiment", "limitation"}:
        non_reference_candidates = [(doc, score) for doc, score, is_ref in candidates if not is_ref]
        if len(non_reference_candidates) >= 6:
            docs_with_scores = non_reference_candidates

    reranked: list[tuple[float, int, object, float]] = []
    for rank, (doc, score) in enumerate(docs_with_scores):
        metadata = dict(getattr(doc, "metadata", {}) or {})
        adjusted_score = float(score)
        section = str(metadata.get("section", "body"))
        source = str(metadata.get("source", "")).lower()
        page = metadata.get("page")
        content = str(getattr(doc, "page_content", "")).lower()

        adjusted_score -= section_boosts.get(section, 0.0)
        adjusted_score -= _keyword_bonus(content, keyword_boosts)
        if query_sources and any(source_hint in source for source_hint in query_sources):
            adjusted_score -= 0.2
        if intent in {"contribution", "summary"} and isinstance(page, int) and page <= 2:
            adjusted_score -= 0.18
        if section == "references" or _looks_like_reference_text(content):
            adjusted_score += 1.0

        reranked.append((adjusted_score, rank, doc, score))

    reranked.sort(key=lambda item: (item[0], item[1]))
    return [(doc, original_score) for _, _, doc, original_score in reranked]


def fuse_retrieval_results(
    dense_results: list[SearchResult],
    bm25_results: list[SearchResult],
    settings: Settings | None = None,
) -> list[SearchResult]:
    settings = settings or get_settings()
    if settings.retrieval_mode == "dense" or not bm25_results:
        return dense_results
    if settings.retrieval_mode == "bm25" or not dense_results:
        results = [result.model_copy(deep=True) for result in bm25_results]
        for rank, result in enumerate(results, start=1):
            result.metadata.setdefault("retrieval_channels", ["bm25"])
            result.metadata.setdefault("bm25_rank", rank)
            result.metadata.setdefault("ranker", "bm25")
        return results

    dense_norm = _normalize_dense_scores(dense_results)
    bm25_norm = _normalize_positive_scores(bm25_results)
    dense_by_key = {_result_key(result): result for result in dense_results}
    bm25_by_key = {_result_key(result): result for result in bm25_results}
    dense_ranks = {_result_key(result): rank for rank, result in enumerate(dense_results)}
    bm25_ranks = {_result_key(result): rank for rank, result in enumerate(bm25_results)}

    combined: dict[tuple, SearchResult] = {}
    ordered_keys: list[tuple] = []
    for result in [*dense_results, *bm25_results]:
        key = _result_key(result)
        if key not in combined:
            combined[key] = result.model_copy(deep=True)
            combined[key].metadata["retrieval_channels"] = []
            ordered_keys.append(key)

    for key in ordered_keys:
        result = combined[key]
        channels: list[str] = []
        dense_score = dense_norm.get(key, 0.0)
        bm25_score = bm25_norm.get(key, 0.0)
        rrf_score = 0.0

        if key in dense_ranks:
            channels.append("dense")
            rrf_score += 1 / (settings.hybrid_rrf_k + dense_ranks[key] + 1)
            result.metadata["dense_rank"] = dense_ranks[key] + 1
            result.metadata["dense_score"] = dense_by_key[key].metadata.get(
                "dense_score", dense_by_key[key].score
            )
        if key in bm25_ranks:
            channels.append("bm25")
            rrf_score += 1 / (settings.hybrid_rrf_k + bm25_ranks[key] + 1)
            result.metadata["bm25_rank"] = bm25_ranks[key] + 1
            result.metadata["bm25_score"] = bm25_by_key[key].metadata.get(
                "bm25_score", bm25_by_key[key].score
            )

        hybrid_score = (
            settings.hybrid_dense_weight * dense_score
            + settings.hybrid_bm25_weight * bm25_score
            + rrf_score
        )
        result.score = hybrid_score
        result.metadata["retrieval_channels"] = channels
        result.metadata["dense_normalized_score"] = dense_score
        result.metadata["bm25_normalized_score"] = bm25_score
        result.metadata["hybrid_score"] = hybrid_score
        result.metadata["ranker"] = "hybrid"

    fused = list(combined.values())
    fused.sort(key=lambda result: (-(result.score or 0.0), _stable_rank(result, dense_ranks, bm25_ranks)))
    return fused


def rerank_search_results_by_section(
    results: list[SearchResult],
    query: str,
    intent: str,
) -> list[SearchResult]:
    if intent == "general":
        return results

    candidates: list[tuple[SearchResult, bool]] = []
    for result in results:
        content = result.content.lower()
        is_reference = result.metadata.get("section") == "references" or _looks_like_reference_text(content)
        candidates.append((result, is_reference))

    if intent in {"contribution", "summary", "method", "experiment", "limitation"}:
        non_reference_results = [result for result, is_ref in candidates if not is_ref]
        if len(non_reference_results) >= 6:
            results = non_reference_results

    section_boosts = INTENT_SECTION_BOOSTS.get(intent, {})
    keyword_boosts = INTENT_KEYWORD_BOOSTS.get(intent, [])
    query_sources = _mentioned_pdf_sources(query)
    scored: list[tuple[float, int, SearchResult]] = []

    for rank, result in enumerate(results):
        adjusted_score = float(result.score or result.metadata.get("hybrid_score", 0.0) or 0.0)
        section = str(result.metadata.get("section", "body"))
        source = result.source.lower()
        content = result.content.lower()

        adjusted_score += section_boosts.get(section, 0.0)
        adjusted_score += _keyword_bonus(content, keyword_boosts)
        if query_sources and any(source_hint in source for source_hint in query_sources):
            adjusted_score += 0.2
        if intent in {"contribution", "summary"} and isinstance(result.page, int) and result.page <= 2:
            adjusted_score += 0.18
        if section == "references" or _looks_like_reference_text(content):
            adjusted_score -= 1.0

        updated = result.model_copy(deep=True)
        updated.score = adjusted_score
        updated.metadata["section_adjusted_score"] = adjusted_score
        scored.append((adjusted_score, rank, updated))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [result for _, _, result in scored]


def _dense_results_from_docs(docs_with_scores: list[tuple[object, float]]) -> list[SearchResult]:
    results: list[SearchResult] = []
    for rank, (doc, score) in enumerate(docs_with_scores, start=1):
        metadata = dict(getattr(doc, "metadata", {}) or {})
        dense_score = float(score) if score is not None else None
        metadata.update(
            {
                "dense_score": dense_score,
                "dense_rank": rank,
                "retrieval_channels": ["dense"],
            }
        )
        results.append(
            SearchResult(
                content=str(getattr(doc, "page_content", "")),
                source=str(metadata.get("source") or metadata.get("source_path") or "unknown"),
                page=metadata.get("page"),
                score=dense_score,
                metadata=metadata,
            )
        )
    return results


def _normalize_dense_scores(results: list[SearchResult]) -> dict[tuple, float]:
    scored = [float(result.score) for result in results if isinstance(result.score, int | float)]
    if not scored:
        return {_result_key(result): 1 / rank for rank, result in enumerate(results, start=1)}
    min_score = min(scored)
    max_score = max(scored)
    if max_score == min_score:
        return {_result_key(result): 1 / rank for rank, result in enumerate(results, start=1)}
    return {
        _result_key(result): 1
        - (
            ((max_score if result.score is None else float(result.score)) - min_score)
            / (max_score - min_score)
        )
        for result in results
    }


def _normalize_positive_scores(results: list[SearchResult]) -> dict[tuple, float]:
    max_score = max((float(result.score or 0.0) for result in results), default=0.0)
    if max_score <= 0:
        return {_result_key(result): 0.0 for result in results}
    return {_result_key(result): float(result.score or 0.0) / max_score for result in results}


def _result_key(result: SearchResult) -> tuple:
    chunk_id = result.metadata.get("chunk_id")
    if chunk_id:
        return ("chunk", str(chunk_id))
    return ("content", result.source, result.page, result.content[:120])


def _stable_rank(
    result: SearchResult,
    dense_ranks: dict[tuple, int],
    bm25_ranks: dict[tuple, int],
) -> int:
    key = _result_key(result)
    return min(dense_ranks.get(key, 10_000), bm25_ranks.get(key, 10_000))


def _keyword_bonus(content: str, keywords: list[str]) -> float:
    hits = sum(1 for keyword in keywords if keyword in content)
    return min(hits * 0.06, 0.24)


def _mentioned_pdf_sources(query: str) -> list[str]:
    lowered = query.lower()
    if "teaching small language models" in lowered:
        return ["teaching_small_language_models"]
    return []


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _looks_like_reference_text(content: str) -> bool:
    content = content.lower()
    reference_markers = [
        "arxiv preprint",
        "association for computational linguistics",
        "conference on",
        "transactions of",
        "journal of",
        "retrieved from",
        "doi:",
    ]
    marker_hits = sum(1 for marker in reference_markers if marker in content)
    year_hits = len(re.findall(r"\b(19|20)\d{2}\b", content))
    return marker_hits >= 1 or year_hits >= 3
