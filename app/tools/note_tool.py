from __future__ import annotations

from app.chains.note_chain import generate_note_answer
from app.retriever.retrieval import search_knowledge_base
from app.utils.response import collect_sources


def run_note_generation(question: str, top_k: int | None = None) -> dict:
    chunks = search_knowledge_base(question, top_k)
    answer = generate_note_answer(question, chunks)
    return {
        "answer": answer,
        "sources": collect_sources(chunks),
        "related_chunks": chunks,
        "tool_result": {"retrieved_chunks": len(chunks), "mode": "note_generation"},
    }
