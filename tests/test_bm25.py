from dataclasses import replace

from app.config import get_settings
from app.retriever.bm25 import bm25_search


def test_bm25_search_returns_keyword_match(tmp_path) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    chunks_path = processed / "chunks.jsonl"
    chunks_path.write_text(
        "\n".join(
            [
                '{"text":"LoRA 使用低秩矩阵减少训练参数。","metadata":{"source":"lora.md","page":1,"chunk_id":"lora_1"}}',
                '{"text":"RAG 使用外部知识库进行检索增强生成。","metadata":{"source":"rag.md","page":1,"chunk_id":"rag_1"}}',
            ]
        ),
        encoding="utf-8",
    )
    settings = replace(get_settings(), processed_docs_path=processed)

    results = bm25_search("低秩矩阵", top_k=1, settings=settings)

    assert len(results) == 1
    assert results[0].source == "lora.md"
    assert results[0].metadata["bm25_score"] > 0

