
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message


def create_conversation(
    db: Session,
    title: str,
) -> Conversation:
    if not title.strip():
        raise ValueError("Title cannot be empty.")

    conversation = Conversation(title=title.strip())

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def add_message(
    db: Session,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
) -> Message:
    if role not in {"user", "assistant"}:
        raise ValueError("Invalid message role.")

    if not content.strip():
        raise ValueError("Message cannot be empty.")

    conversation = db.get(
        Conversation,
        conversation_id,
    )

    if conversation is None:
        raise ValueError("Conversation not found.")

    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content.strip(),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


def get_conversation_messages(
    db: Session,
    conversation_id: uuid.UUID,
) -> list[Message]:
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )

    return list(db.scalars(statement).all())