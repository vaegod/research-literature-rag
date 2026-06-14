from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "research-literature-rag-agent"


def test_frontend_home() -> None:
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "科研文献智能问答" in response.text
