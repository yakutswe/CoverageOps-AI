
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


class EvidenceReference(BaseModel):
    document_id: UUID
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1)


class Finding(BaseModel):
    field_name: str
    observed_value: str | None = None
    requirement: str | None = None
    needs_review: bool = False
    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )


class AgentHandoff(BaseModel):
    handoff_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    from_agent: str = Field(min_length=1)
    to_agent: str = Field(min_length=1)
    status: WorkflowStatus = WorkflowStatus.PENDING
    summary: str = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list)
