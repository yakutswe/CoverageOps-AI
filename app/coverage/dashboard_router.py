"""Synthetic demo dashboard endpoints. Install after review; not a production API."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import (
    CoverageCustomer, CoverageWorkflow, CoverageWorkflowEvent,
    CoverageReviewHandoff,
)
from app.coverage.policy_contracts import InsurancePolicy, CoverageRequirement
from app.coverage.services.policy_review import (
    execute_policy_review, PolicyReviewConflictError,
)

router = APIRouter(prefix="/coverage", tags=["CoverageOps Dashboard"])


class PolicyReviewRequest(BaseModel):
    policy: InsurancePolicy
    requirements: list[CoverageRequirement] = Field(min_length=1)


@router.get("/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db)):
    # Counts are sourced from database records; no synthetic numbers.
    total_workflows = db.scalar(select(func.count()).select_from(CoverageWorkflow)) or 0
    active_workflows = db.scalar(select(func.count()).select_from(CoverageWorkflow).where(
        CoverageWorkflow.status.in_(["pending", "running", "needs_review"])
    )) or 0
    pending_reviews = db.scalar(select(func.count()).select_from(CoverageReviewHandoff).where(
        CoverageReviewHandoff.status == "pending"
    )) or 0
    reviewed_handoffs = db.scalar(select(func.count()).select_from(CoverageReviewHandoff).where(
        CoverageReviewHandoff.status != "pending"
    )) or 0
    # JSON findings stored in handoffs, including only confirmed saved findings.
    flagged = 0
    reviews = db.scalars(select(CoverageReviewHandoff.findings)).all()
    for findings in reviews:
        if isinstance(findings, list):
            flagged += sum(
                isinstance(f, dict) and f.get("status") in
                {"below_requirement", "missing_information", "needs_review"}
                for f in findings
            )
    return {
        "total_workflows": total_workflows,
        "active_workflows": active_workflows,
        "pending_reviews": pending_reviews,
        "reviewed_handoffs": reviewed_handoffs,
        "discrepancy_findings": flagged,
    }


@router.get("/dashboard/reviews")
def dashboard_reviews(db: Session = Depends(get_db)):
    rows = db.execute(
        select(CoverageReviewHandoff, CoverageWorkflow, CoverageCustomer.company_name)
        .join(CoverageWorkflow, CoverageReviewHandoff.workflow_id == CoverageWorkflow.id)
        .join(CoverageCustomer, CoverageWorkflow.customer_id == CoverageCustomer.id)
        .where(CoverageReviewHandoff.status == "pending")
        .order_by(CoverageReviewHandoff.created_at.asc())
        .limit(100)
    ).all()
    return [
        {
            "handoff_id": str(handoff.id),
            "workflow_id": str(workflow.id),
            "customer_name": company_name,
            "status": handoff.status,
            "current_step": workflow.current_step,
            "summary": handoff.summary,
            "created_at": handoff.created_at.isoformat(),
            "findings": handoff.findings,
        }
        for handoff, workflow, company_name in rows
    ]


@router.post("/workflows/{workflow_id}/policy-review")
async def post_policy_review(
    workflow_id: UUID,
    request: PolicyReviewRequest,
    db: Session = Depends(get_db),
):
    try:
        return await execute_policy_review(
            db=db,
            workflow_id=workflow_id,
            payload=request.model_dump(mode="json"),
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PolicyReviewConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/workflows/{workflow_id}/insurance-results")
def get_insurance_results(workflow_id: UUID, db: Session = Depends(get_db)):
    workflow = db.get(CoverageWorkflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    events = db.scalars(
        select(CoverageWorkflowEvent)
        .where(
            CoverageWorkflowEvent.workflow_id == workflow_id,
            CoverageWorkflowEvent.event_type.in_([
                "insurance_agent_completed", "insurance_review_requested", "handoff_reviewed"
            ]),
        )
        .order_by(CoverageWorkflowEvent.created_at, CoverageWorkflowEvent.id)
    ).all()
    return {
        "workflow_id": str(workflow_id),
        "events": [
            {"event_type": e.event_type, "actor": e.actor,
             "details": e.details, "created_at": e.created_at.isoformat()}
            for e in events
        ],
    }
