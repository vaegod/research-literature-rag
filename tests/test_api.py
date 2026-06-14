from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import RAGResponse, SearchResult, Source


def test_knowledge_search_api(monkeypatch) -> None:
    def fake_search(query: str, top_k: int | None = None):
        return [
            SearchResult(
                content="知识蒸馏使用教师模型的软标签指导学生模型。",
                source="knowledge_distillation_survey.md",
                page=1,
                score=0.2,
                metadata={"chunk_id": "kd_chunk_0001"},
            )
        ]

    monkeypatch.setattr("app.api.knowledge.search", fake_search)
    client = TestClient(app)
    response = client.post("/knowledge/search", json={"query": "知识蒸馏", "top_k": 1})

    assert response.status_code == 200
    data = response.json()
    assert data["top_k"] == 1
    assert data["results"][0]["source"] == "knowledge_distillation_survey.md"


def test_rag_chat_api(monkeypatch) -> None:
    def fake_ask_rag(question: str, top_k: int | None = None):
        return RAGResponse(
            answer="知识蒸馏使用教师模型指导学生模型。",
            sources=[Source(source="knowledge_distillation_survey.md", page=1, chunk_id="kd_0001")],
            related_chunks=[],
        )

    monkeypatch.setattr("app.api.chat.ask_rag", fake_ask_rag)
    client = TestClient(app)
    response = client.post("/chat/rag", json={"question": "知识蒸馏是什么？"})

    assert response.status_code == 200
    assert "教师模型" in response.json()["answer"]


def test_rag_stream_api(monkeypatch) -> None:
    chunks = [
        SearchResult(
            content="RAG 需要返回引用来源。",
            source="rag_for_llm_applications.md",
            page=1,
            score=0.8,
            metadata={"chunk_id": "rag_for_llm_applications_chunk_0001"},
        )
    ]

    monkeypatch.setattr("app.api.chat.search_rag", lambda question, top_k=None: chunks)
    monkeypatch.setattr(
        "app.api.chat.generate_rag_answer_stream",
        lambda question, related_chunks: iter(["RAG ", "需要引用。"]),
    )

    client = TestClient(app)
    response = client.post("/chat/rag/stream", json={"question": "为什么需要引用？"})

    assert response.status_code == 200
    body = response.text
    assert "event: meta" in body
    assert "event: delta" in body
    assert "RAG " in body
    assert "event: done" in body


def test_experiment_search_api() -> None:
    client = TestClient(app)
    response = client.post("/experiments/search", json={"query": "EXP-003"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["results"][0]["dataset"] == "AG-NEWS"


def test_document_crud_api(tmp_path, monkeypatch) -> None:
    from dataclasses import replace

    import app.services.document_service as document_service
    from app.config import get_settings

    settings = replace(
        get_settings(),
        raw_docs_path=tmp_path,
        processed_docs_path=tmp_path / "processed",
    )
    monkeypatch.setattr(document_service, "get_settings", lambda: settings)
    tmp_path.joinpath("processed").mkdir()

    client = TestClient(app)
    create_response = client.post(
        "/documents",
        json={"filename": "browser_note.md", "content": "# Browser Note\n\nhello"},
    )
    assert create_response.status_code == 200

    list_response = client.get("/documents")
    assert list_response.status_code == 200
    assert list_response.json()["documents"][0]["filename"] == "browser_note.md"

    read_response = client.get("/documents/browser_note.md")
    assert read_response.status_code == 200
    assert "Browser Note" in read_response.json()["content"]

    update_response = client.put(
        "/documents/browser_note.md",
        json={"content": "# Browser Note\n\nupdated"},
    )
    assert update_response.status_code == 200

    delete_response = client.delete("/documents/browser_note.md")
    assert delete_response.status_code == 200
