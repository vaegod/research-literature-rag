from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.models.schemas import SearchResult


@dataclass(frozen=True)
class _BM25Document:
    result: SearchResult
    tokens: list[str]
    term_freq: Counter[str]


def bm25_search(
    query: str,
    top_k: int,
    settings: Settings | None = None,
) -> list[SearchResult]:
    settings = settings or get_settings()
    documents = _load_bm25_documents(settings)
    if not documents:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    doc_count = len(documents)
    avg_doc_len = sum(len(doc.tokens) for doc in documents) / doc_count
    doc_freq = _document_frequency(documents)
    scored: list[tuple[float, int, SearchResult]] = []

    for index, doc in enumerate(documents):
        score = _bm25_score(query_tokens, doc, doc_count, avg_doc_len, doc_freq)
        if score <= 0:
            continue
        result = doc.result.model_copy(deep=True)
        result.score = score
        result.metadata.update(
            {
                "bm25_score": score,
                "bm25_rank": index,
                "retrieval_channels": ["bm25"],
            }
        )
        scored.append((score, index, result))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [result for _, _, result in scored[:top_k]]


def _load_bm25_documents(settings: Settings) -> list[_BM25Document]:
    chunks_path = settings.processed_docs_path / "chunks.jsonl"
    if not chunks_path.exists():
        return []

    documents: list[_BM25Document] = []
    with chunks_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            payload = json.loads(line)
            text = str(payload.get("text", ""))
            metadata = dict(payload.get("metadata", {}) or {})
            if not text.strip():
                continue
            tokens = _tokenize(text)
            if not tokens:
                continue
            result = SearchResult(
                content=text,
                source=str(metadata.get("source") or metadata.get("source_path") or "unknown"),
                page=metadata.get("page"),
                score=None,
                metadata=metadata,
            )
            documents.append(
                _BM25Document(result=result, tokens=tokens, term_freq=Counter(tokens))
            )
    return documents


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text, flags=re.IGNORECASE)

    for chinese_text in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        tokens.extend(chinese_text[index : index + 2] for index in range(len(chinese_text) - 1))

    return tokens


def _document_frequency(documents: list[_BM25Document]) -> Counter[str]:
    doc_freq: Counter[str] = Counter()
    for doc in documents:
        doc_freq.update(set(doc.tokens))
    return doc_freq


def _bm25_score(
    query_tokens: list[str],
    document: _BM25Document,
    doc_count: int,
    avg_doc_len: float,
    doc_freq: Counter[str],
) -> float:
    k1 = 1.5
    b = 0.75
    doc_len = max(len(document.tokens), 1)
    score = 0.0

    for token in query_tokens:
        frequency = document.term_freq.get(token, 0)
        if frequency == 0:
            continue
        containing_docs = doc_freq.get(token, 0)
        idf = math.log(1 + (doc_count - containing_docs + 0.5) / (containing_docs + 0.5))
        denominator = frequency + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1))
        score += idf * (frequency * (k1 + 1)) / denominator
    return score

