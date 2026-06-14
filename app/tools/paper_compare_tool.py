from __future__ import annotations

from app.chains.compare_chain import generate_compare_answer
from app.retriever.retrieval import search_knowledge_base
from app.utils.response import collect_sources


def run_paper_compare(question: str, top_k: int | None = None) -> dict:
    chunks = search_knowledge_base(question, top_k)
    answer = generate_compare_answer(question, chunks)
    return {
        "answer": answer,
        "sources": collect_sources(chunks),
        "related_chunks": chunks,
        "tool_result": {"retrieved_chunks": len(chunks), "mode": "paper_compare"},
    }
