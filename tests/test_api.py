
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_research_rejects_empty_task():
    response = client.post(
        "/agents/research",
        json={"task": ""},
    )

    assert response.status_code == 422


def test_research_success(monkeypatch):
    async def fake_run(self, task):
        return {
            "agent": "research",
            "task": task,
            "status": "completed",
            "answer": "AI agents can use tools.",
            "model": "qwen3:1.7b",
            "sources": [],
        }

    monkeypatch.setattr(
        "app.main.ResearchAgent.run",
        fake_run,
    )

    response = client.post(
        "/agents/research",
        json={"task": "Explain AI agents"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert "AI agents" in response.json()["answer"]


def test_research_ollama_failure(monkeypatch):
    from app.core.ollama_client import OllamaError

    async def fake_run(self, task):
        raise OllamaError("Ollama is unavailable")

    monkeypatch.setattr(
        "app.main.ResearchAgent.run",
        fake_run,
    )

    response = client.post(
        "/agents/research",
        json={"task": "Explain AI agents"},
    )

    assert response.status_code == 503
    assert "unavailable" in response.json()["detail"]