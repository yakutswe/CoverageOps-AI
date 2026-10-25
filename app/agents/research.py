
from app.core.agent_loop import AgentLoop
from app.core.ollama_client import OllamaClient


SYSTEM_PROMPT = """
You are the Research Agent in Agent Lab.

Your job:
- Understand the user's task.
- Choose an available tool when useful.
- Use actual tool results in your answer.
- Never invent a tool result.
- Never claim to have browsed the internet.
- Report uncertainty when appropriate.
- Keep answers accurate and concise.

You have two possible tools:
1. calculate: basic arithmetic
2. lookup_concept: definitions of agent concepts

You do not have web search, file modification,
shell execution, or persistent memory.

If a tool returns an error, explain the problem
or try an allowed alternative.
"""


class ResearchAgent:
    def __init__(
        self,
        client: OllamaClient | None = None,
    ):
        self.client = client or OllamaClient()
        self.loop = AgentLoop(self.client)

    async def run(self, task: str) -> dict:
        result = await self.loop.run(
            task=task,
            system_prompt=SYSTEM_PROMPT,
        )

        return {
            "agent": "research",
            "task": task,
            "status": result["status"],
            "answer": result["answer"],
            "model": self.client.settings.ollama_model,
            "sources": [],
            "run_id": result["run_id"],
            "tool_steps": result["tool_steps"],
            "trace": result["trace"],
        }
