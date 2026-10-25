
import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.core.ollama_client import OllamaClient, OllamaError


def make_settings():
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="qwen3:1.7b",
        ollama_timeout_seconds=10,
    )


def test_ollama_chat_success():
    def handler(request: httpx.Request):
        assert request.url.path == "/api/chat"

        import json
        payload = json.loads(request.content)

        assert payload["model"] == "qwen3:1.7b"
        assert payload["stream"] is False

        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "Hello from local Qwen.",
                }
            },
        )

    client = OllamaClient(
        settings=make_settings(),
        transport=httpx.MockTransport(handler),
    )

    answer = asyncio.run(
        client.chat([
            {"role": "user", "content": "Hello"}
        ])
    )

    assert answer == "Hello from local Qwen."


def test_ollama_empty_response():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"message": {"content": ""}},
        )
    )

    client = OllamaClient(
        settings=make_settings(),
        transport=transport,
    )

    with pytest.raises(OllamaError, match="empty"):
        asyncio.run(
            client.chat([
                {"role": "user", "content": "Hello"}
            ])
        )


def test_ollama_http_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            404,
            json={"error": "model not found"},
        )
    )

    client = OllamaClient(
        settings=make_settings(),
        transport=transport,
    )

    with pytest.raises(OllamaError, match="HTTP 404"):
        asyncio.run(
            client.chat([
                {"role": "user", "content": "Hello"}
            ])
        )


def test_ollama_connection_error():
    def handler(request):
        raise httpx.ConnectError(
            "Connection refused",
            request=request,
        )

    client = OllamaClient(
        settings=make_settings(),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OllamaError, match="connect"):
        asyncio.run(
            client.chat([
                {"role": "user", "content": "Hello"}
            ])
        )