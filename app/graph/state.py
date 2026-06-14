from __future__ import annotations

from typing import Any, TypedDict

from app.models.schemas import SearchResult, Source


class AgentState(TypedDict, total=False):
    question: str
    top_k: int
    intent: str
    router: str
    router_confidence: float
    router_reason: str
    answer: str
    sources: list[Source]
    related_chunks: list[SearchResult]
    tool_result: dict[str, Any]
