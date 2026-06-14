from __future__ import annotations

from app.chains.rag_chain import generate_rag_answer
from app.models.schemas import RAGResponse
from app.retriever.retrieval import search_knowledge_base
from app.utils.response import collect_sources


def search(query: str, top_k: int | None = None):
    return search_knowledge_base(query, top_k)


def ask_rag(question: str, top_k: int | None = None) -> RAGResponse:
    chunks = search_knowledge_base(question, top_k)
    answer = generate_rag_answer(question, chunks)
    return RAGResponse(
        answer=answer,
        sources=collect_sources(chunks),
        related_chunks=chunks,
    )
