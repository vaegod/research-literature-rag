from app.retriever import retrieval


class DummyDoc:
    def __init__(self, content: str, metadata: dict) -> None:
        self.page_content = content
        self.metadata = metadata


def test_search_knowledge_base_formats_results(monkeypatch) -> None:
    def fake_similarity_search(query, top_k=None, settings=None):
        return [
            (
                DummyDoc(
                    "LoRA 使用低秩矩阵减少训练参数。",
                    {"source": "lora_finetuning_notes.md", "page": 1, "chunk_id": "lora_0001"},
                ),
                0.12,
            )
        ]

    monkeypatch.setattr(retrieval, "similarity_search", fake_similarity_search)
    monkeypatch.setattr(retrieval, "bm25_search", lambda query, top_k, settings=None: [])
    monkeypatch.setattr(
        retrieval,
        "rerank_results",
        lambda query, results, top_n, settings=None: results[:top_n],
    )

    results = retrieval.search_knowledge_base("LoRA", top_k=1)

    assert len(results) == 1
    assert results[0].source == "lora_finetuning_notes.md"
    assert results[0].score == 0.12
    assert "低秩矩阵" in results[0].content


def test_contribution_question_prefers_intro_sections(monkeypatch) -> None:
    def fake_similarity_search(query, top_k=None, settings=None):
        assert "main contribution" in query
        return [
            (
                DummyDoc(
                    "unrelated citation details",
                    {"source": "paper.pdf", "page": 9, "chunk_id": "paper_0009", "section": "references"},
                ),
                0.1,
            ),
            (
                DummyDoc(
                    "The paper proposes a new method and lists the main contributions.",
                    {"source": "paper.pdf", "page": 1, "chunk_id": "paper_0001", "section": "introduction"},
                ),
                0.2,
            ),
        ]

    monkeypatch.setattr(retrieval, "similarity_search", fake_similarity_search)
    monkeypatch.setattr(retrieval, "bm25_search", lambda query, top_k, settings=None: [])
    monkeypatch.setattr(
        retrieval,
        "rerank_results",
        lambda query, results, top_n, settings=None: results[:top_n],
    )

    results = retrieval.search_knowledge_base("这篇论文的主要贡献是什么？", top_k=1)

    assert results[0].metadata["section"] == "introduction"
    assert results[0].metadata["chunk_id"] == "paper_0001"


def test_hybrid_search_uses_bm25_when_dense_misses(monkeypatch) -> None:
    bm25_result = retrieval.SearchResult(
        content="RAG 检索可以通过 BM25 和向量检索进行混合召回。",
        source="rag_for_llm_applications.md",
        page=1,
        score=8.0,
        metadata={"chunk_id": "rag_0001", "section": "method"},
    )

    monkeypatch.setattr(retrieval, "similarity_search", lambda **kwargs: [])
    monkeypatch.setattr(retrieval, "bm25_search", lambda query, top_k, settings=None: [bm25_result])
    monkeypatch.setattr(
        retrieval,
        "rerank_results",
        lambda query, results, top_n, settings=None: results[:top_n],
    )

    results = retrieval.search_knowledge_base("BM25 混合检索", top_k=1)

    assert results[0].source == "rag_for_llm_applications.md"
    assert "bm25" in results[0].metadata["retrieval_channels"]
    assert results[0].metadata["ranker"] == "bm25"
