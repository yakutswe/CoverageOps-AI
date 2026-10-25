from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import uuid

from app.coverage.router import router as coverage_router
from app.coverage.dashboard_router import router as dashboard_router

from app.agents.research import ResearchAgent
from app.core.ollama_client import OllamaError
from app.db.session import get_db
from app.memory.conversation_agent import ConversationAgent
from app.memory.service import create_conversation


app = FastAPI(
    title="Agent Lab API",
    description="Multi-agent AI engineering platform",
    version="0.2.0",
)

app.include_router(coverage_router)
app.include_router(dashboard_router)

class ResearchRequest(BaseModel):
    task: str = Field(min_length=1)


@app.get("/")
def root():
    return {
        "project": "Agent Lab",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/agents/research")
async def research(request: ResearchRequest):
    agent = ResearchAgent()

    try:
        return await agent.run(request.task)

    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
        

@app.post("/conversations")
def new_conversation(
    title: str,
    db: Session = Depends(get_db),
):
    conversation = create_conversation(db, title)

    return {
        "conversation_id": str(conversation.id),
        "title": conversation.title,
    }


class ConversationRequest(BaseModel):
    task: str = Field(min_length=1)


@app.post("/conversations/{conversation_id}/chat")
async def conversation_chat(
    conversation_id: uuid.UUID,
    request: ConversationRequest,
    db: Session = Depends(get_db),
):
    agent = ConversationAgent()

    try:
        return await agent.run(
            db=db,
            conversation_id=conversation_id,
            task=request.task,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404
            if str(exc) == "Conversation not found."
            else 400,
            detail=str(exc),
        ) from exc

    except OllamaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
