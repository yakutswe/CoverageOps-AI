
import asyncio
from typing import Any, cast

from app.agents.research import ResearchAgent
from app.core.config import Settings


class FakeOllamaClient:
    def __init__(self):
        self.settings = Settings(
            ollama_model="qwen3:1.7b",
        )
        self.messages = None
        self.tools = None

    async def chat_turn(self, messages, tools=None):
        self.messages = messages
        self.tools = tools

        return {
            "role": "assistant",
            "content": (
                "An agent can choose actions "
                "and use tools."
            ),
        }


def test_research_agent_uses_model():
    fake_client = FakeOllamaClient()

    agent = ResearchAgent(
        client=cast(Any, fake_client)
    )

    result = asyncio.run(
        agent.run("What is an AI agent?")
    )

    assert result["status"] == "completed"
    assert result["agent"] == "research"
    assert result["model"] == "qwen3:1.7b"
    assert "choose actions" in result["answer"]
    assert result["sources"] == []
    assert result["tool_steps"] == 0
    assert result["trace"] == []

    assert fake_client.messages is not None
    assert fake_client.messages[0]["role"] == "system"
    assert fake_client.messages[1]["role"] == "user"
    assert fake_client.tools is not None
    assert len(fake_client.tools) == 2
