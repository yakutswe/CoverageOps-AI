from app.coverage.services.resubmission import (
    ResubmissionConflictError,
    resubmit_customer_intake,
)

from app.coverage.services.workflow import execute_onboarding
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import CoverageWorkflow
from app.coverage.services.onboarding import (
    create_customer_workflow,
    get_workflow_events,
)

router = APIRouter(
    prefix="/coverage",
    tags=["CoverageOps AI"],
)

from app.coverage.services.review import (
    ReviewDecision,
    ReviewConflictError,
    review_handoff,
)

class CustomerOnboardingRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    industry: str = Field(min_length=1, max_length=100)


@router.post("/onboarding", status_code=201)
def start_onboarding(
    request: CustomerOnboardingRequest,
    db: Session = Depends(get_db),
):
    try:
        return create_customer_workflow(
            db=db,
            company_name=request.company_name,
            industry=request.industry,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


@router.get("/workflows/{workflow_id}")
def get_coverage_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
):
    workflow = db.get(CoverageWorkflow, workflow_id)

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Coverage workflow not found",
        )

    events = get_workflow_events(db, workflow_id)

    return {
        "workflow_id": str(workflow.id),
        "customer_id": str(workflow.customer_id),
        "status": workflow.status,
        "current_step": workflow.current_step,
        "events": [
            {
                "event_type": event.event_type,
                "actor": event.actor,
                "details": event.details,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }

class IntakeExecutionRequest(BaseModel):
    company_name: str | None = None
    industry: str | None = None


@router.post("/workflows/{workflow_id}/execute")
async def execute_coverage_workflow(
    workflow_id: UUID,
    request: IntakeExecutionRequest,
    db: Session = Depends(get_db),
):
    try:
        return await execute_onboarding(
            db=db,
            workflow_id=workflow_id,
            intake_payload=request.model_dump(
                exclude_none=True
            ),
        )

    except ValueError as exc:
        status_code = (
            404
            if str(exc) == "Workflow not found"
            else 409
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc

class HandoffReviewRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=100)
    decision: ReviewDecision
    notes: str = Field(min_length=1, max_length=2000)


@router.post("/handoffs/{handoff_id}/review")
def submit_handoff_review(
    handoff_id: UUID,
    request: HandoffReviewRequest,
    db: Session = Depends(get_db),
):
    try:
        return review_handoff(
            db=db,
            handoff_id=handoff_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            notes=request.notes,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ReviewConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

class CustomerResubmissionRequest(BaseModel):
    industry: str = Field(min_length=1, max_length=100)


@router.post("/workflows/{workflow_id}/resubmit")
async def resubmit_coverage_intake(
    workflow_id: UUID,
    request: CustomerResubmissionRequest,
    db: Session = Depends(get_db),
):
    try:
        return await resubmit_customer_intake(
            db=db,
            workflow_id=workflow_id,
            industry=request.industry,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except ResubmissionConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc