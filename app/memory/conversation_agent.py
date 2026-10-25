
import uuid

from sqlalchemy.orm import Session

from app.agents.research import ResearchAgent
from app.core.agent_loop import AgentLoop
from app.memory.service import (
    add_message,
    get_conversation_messages,
)
from app.db.models import Conversation


class ConversationAgent:
    def __init__(self, client=None):
        self.research_agent = ResearchAgent(client=client)

    async def run(
        self,
        db: Session,
        conversation_id: uuid.UUID,
        task: str,
    ) -> dict:
        if not task.strip():
            raise ValueError("Task cannot be empty.")

        conversation = db.get(
            Conversation,
            conversation_id,
        )

        if conversation is None:
            raise ValueError("Conversation not found.")

        history = get_conversation_messages(
            db,
            conversation_id,
        )

        # For now, take the most recent messages.
        recent = history[-10:]

        context = "\n".join(
            f"{message.role}: {message.content}"
            for message in recent
        )

        enriched_task = (
            "Previous conversation:\n"
            f"{context}\n\n"
            "Current request:\n"
            f"{task}"
        )

        result = await self.research_agent.run(
            enriched_task
        )

        if result["status"] == "completed":
            add_message(
                db,
                conversation_id,
                "user",
                task,
            )

            add_message(
                db,
                conversation_id,
                "assistant",
                result["answer"],
            )

        return {
            **result,
            "conversation_id": str(conversation_id),
        }