from dataclasses import replace

from app.config import get_settings
from app.models.schemas import SearchResult
from app.retriever.reranker import rerank_results


class DummyResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "results": [
                {"index": 1, "relevance_score": 0.98},
                {"index": 0, "relevance_score": 0.12},
            ]
        }


def test_siliconflow_reranker_reorders_by_provider_index(monkeypatch) -> None:
    settings = replace(
        get_settings(),
        openai_compatible_api_key="test-key",
        enable_reranker=True,
        reranker_model="BAAI/bge-reranker-v2-m3",
    )

    def fake_post(url, headers, json, timeout):
        assert url == "https://api.siliconflow.cn/v1/rerank"
        assert headers["Authorization"] == "Bearer test-key"
        assert json["model"] == "BAAI/bge-reranker-v2-m3"
        assert json["query"] == "LoRA"
        assert json["documents"] == ["first", "second"]
        return DummyResponse()

    import app.retriever.reranker as reranker

    monkeypatch.setattr(reranker.httpx, "post", fake_post)
    results = [
        SearchResult(content="first", source="a.md", metadata={"chunk_id": "a"}),
        SearchResult(content="second", source="b.md", metadata={"chunk_id": "b"}),
    ]

    reranked = rerank_results("LoRA", results, top_n=2, settings=settings)

    assert reranked[0].source == "b.md"
    assert reranked[0].score == 0.98
    assert reranked[0].metadata["ranker"] == "siliconflow_reranker"

