from __future__ import annotations

from app.models.schemas import SearchResult, Source


def collect_sources(chunks: list[SearchResult]) -> list[Source]:
    seen: set[tuple[str, int | None, str | None]] = set()
    sources: list[Source] = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get("chunk_id")
        item = (chunk.source, chunk.page, chunk_id)
        if item in seen:
            continue
        seen.add(item)
        sources.append(Source(source=chunk.source, page=chunk.page, chunk_id=chunk_id))
    return sources
