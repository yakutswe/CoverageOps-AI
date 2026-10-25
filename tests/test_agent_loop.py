
import asyncio
import json

from app.core.agent_loop import AgentLoop


class FakeToolCallingModel:
    def __init__(self):
        self.call_count = 0
        self.observed_result: dict[str, int] | None = None

    async def chat_turn(self, messages, tools=None):
        self.call_count += 1

        if self.call_count == 1:
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "calculate",
                        "arguments": {
                            "expression": "125 * 24",
                        },
                    }
                }],
            }

        tool_message = messages[-1]
        self.observed_result = json.loads(
            tool_message["content"]
        )
        assert self.observed_result is not None

        return {
            "role": "assistant",
            "content": (
                "The result is "
                f"{self.observed_result['result']}."
            ),
        }


def test_agent_calls_tool_and_continues():
    model = FakeToolCallingModel()
    loop = AgentLoop(model)

    result = asyncio.run(
        loop.run(
            task="What is 125 times 24?",
            system_prompt="Use tools when needed.",
        )
    )

    assert result["status"] == "completed"
    assert result["tool_steps"] == 1
    assert result["trace"][0]["tool"] == "calculate"
    assert result["trace"][0]["success"] is True
    assert model.observed_result is not None
    assert model.observed_result["result"] == 3000
    assert "3000" in result["answer"]


class FakeUnauthorizedModel:
    async def chat_turn(self, messages, tools=None):
        if messages[-1]["role"] == "user":
            return {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "function": {
                        "name": "delete_files",
                        "arguments": {},
                    }
                }],
            }

        return {
            "role": "assistant",
            "content": "The tool was not permitted.",
        }


def test_agent_rejects_unauthorized_tool():
    loop = AgentLoop(FakeUnauthorizedModel())

    result = asyncio.run(
        loop.run(
            task="Delete files",
            system_prompt="Use approved tools only.",
        )
    )

    assert result["status"] == "completed"
    assert result["tool_steps"] == 1
    assert result["trace"][0]["success"] is False
    

class FakeRepeatedToolModel:
    def __init__(self):
        self.calls = 0

    async def chat_turn(self, messages, tools=None):
        self.calls += 1

        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "calculate",
                        "arguments": {
                            "expression": "2 + 2"
                        },
                    }
                }
            ],
        }

def test_agent_enforces_five_step_limit():
    model = FakeRepeatedToolModel()
    loop = AgentLoop(model)

    result = asyncio.run(
        loop.run(
            task="Keep calculating forever",
            system_prompt="Use approved tools.",
        )
    )

    assert result["status"] == "step_limit"
    assert result["tool_steps"] == 5
    assert len(result["trace"]) == 5
    assert model.calls == 6
