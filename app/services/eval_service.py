from __future__ import annotations

import csv
import time

from app.config import Settings, get_settings
from app.graph.workflow import run_agent
from app.models.schemas import EvalCaseResult, EvalRunResponse


def _split_sources(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _split_keywords(value: str) -> list[str]:
    normalized = value.replace("；", ";").replace("、", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def _split_chunk_ids(value: str) -> list[str]:
    normalized = value.replace("；", ";").replace("、", ";").replace("|", ";")
    return [item.strip() for item in normalized.split(";") if item.strip()]


def _source_hit(sources: list, expected_source: str) -> bool:
    expected = _split_sources(expected_source)
    if not expected:
        return False
    observed = " ".join(str(getattr(source, "source", source)) for source in sources)
    return any(item in observed for item in expected)


def _keyword_hit(answer: str, expected_keywords: str) -> bool:
    keywords = _split_keywords(expected_keywords)
    if not keywords:
        return False
    hit_count = sum(1 for keyword in keywords if keyword in answer)
    return hit_count / len(keywords) >= 0.5


def _observed_chunk_ids(state: dict) -> list[str]:
    chunk_ids: list[str] = []
    for chunk in state.get("related_chunks", []) or []:
        metadata = getattr(chunk, "metadata", None)
        if metadata is None and isinstance(chunk, dict):
            metadata = chunk.get("metadata", {})
        metadata = metadata or {}
        chunk_id = metadata.get("chunk_id")
        if chunk_id:
            chunk_ids.append(str(chunk_id))
    return chunk_ids


def _retrieval_metrics(expected_chunk_ids: list[str], observed_chunk_ids: list[str]) -> tuple[bool, float]:
    if not expected_chunk_ids:
        return False, 0.0

    expected = set(expected_chunk_ids)
    for index, chunk_id in enumerate(observed_chunk_ids, start=1):
        if chunk_id in expected:
            return True, round(1 / index, 4)
    return False, 0.0


def run_eval(limit: int | None = None, settings: Settings | None = None) -> EvalRunResponse:
    settings = settings or get_settings()
    results: list[EvalCaseResult] = []
    source_hits = 0
    keyword_hits = 0
    retrieval_cases = 0
    retrieval_hits = 0
    reciprocal_rank_sum = 0.0
    latencies: list[float] = []

    with settings.eval_questions_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    if limit:
        rows = rows[:limit]

    output_rows: list[dict] = []
    for row in rows:
        start = time.perf_counter()
        state = {}
        answer = ""
        sources = []
        error_message = ""
        try:
            state = run_agent(row["question"])
            answer = state.get("answer", "")
            sources = state.get("sources", [])
        except Exception as exc:  # pragma: no cover - depends on external model provider.
            error_message = f"{type(exc).__name__}: {exc}"
            answer = f"评测样例执行失败：{error_message}"
        latency = time.perf_counter() - start
        latencies.append(latency)

        source_ok = _source_hit(sources, row.get("expected_source", ""))
        if not source_ok and row.get("expected_source") == "experiment_records.json":
            source_ok = state.get("tool_result", {}).get("total", 0) > 0
        if not source_ok and row.get("expected_source") == "general_chat":
            source_ok = state.get("intent") == "general_chat"
        keyword_ok = _keyword_hit(answer, row.get("expected_keywords", ""))
        expected_chunk_ids = _split_chunk_ids(row.get("expected_chunk_ids", ""))
        observed_chunk_ids = _observed_chunk_ids(state)
        retrieval_hit: bool | None = None
        reciprocal_rank: float | None = None
        if expected_chunk_ids:
            retrieval_cases += 1
            retrieval_hit, reciprocal_rank = _retrieval_metrics(expected_chunk_ids, observed_chunk_ids)
            retrieval_hits += int(retrieval_hit)
            reciprocal_rank_sum += reciprocal_rank
        source_hits += int(source_ok)
        keyword_hits += int(keyword_ok)

        case = EvalCaseResult(
            id=row["id"],
            question=row["question"],
            intent=row.get("intent", ""),
            source_hit=source_ok,
            keyword_hit=keyword_ok,
            retrieval_hit=retrieval_hit,
            reciprocal_rank=reciprocal_rank,
            latency=round(latency, 3),
            answer_preview=(error_message or answer)[:200].replace("\n", " "),
            expected_chunk_ids=expected_chunk_ids,
            observed_chunk_ids=observed_chunk_ids,
        )
        results.append(case)
        output_rows.append(case.model_dump())

    _write_eval_result(output_rows, settings)
    total = len(rows)
    failed_cases = [
        case
        for case in results
        if not case.source_hit or not case.keyword_hit or case.retrieval_hit is False
    ]
    return EvalRunResponse(
        total=total,
        source_hit_rate=source_hits / total if total else 0.0,
        keyword_hit_rate=keyword_hits / total if total else 0.0,
        retrieval_recall_at_k=retrieval_hits / retrieval_cases if retrieval_cases else 0.0,
        mean_reciprocal_rank=reciprocal_rank_sum / retrieval_cases if retrieval_cases else 0.0,
        avg_latency=sum(latencies) / total if total else 0.0,
        failed_cases=failed_cases,
    )


def _write_eval_result(rows: list[dict], settings: Settings) -> None:
    settings.eval_result_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "question",
        "intent",
        "source_hit",
        "keyword_hit",
        "retrieval_hit",
        "reciprocal_rank",
        "latency",
        "answer_preview",
        "expected_chunk_ids",
        "observed_chunk_ids",
    ]
    with settings.eval_result_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
