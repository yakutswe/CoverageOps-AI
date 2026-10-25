
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CoverageReviewHandoff,
    CoverageWorkflow,
    CoverageWorkflowEvent,
)


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class ReviewConflictError(Exception):
    pass


def review_handoff(
    db: Session,
    handoff_id: UUID,
    reviewer_id: str,
    decision: ReviewDecision,
    notes: str,
) -> dict:
    reviewer_id = reviewer_id.strip()
    notes = notes.strip()

    if not reviewer_id:
        raise ValueError("Reviewer ID is required.")

    if not notes:
        raise ValueError("Review notes are required.")

    try:
        # Lock the handoff before checking or changing its state.
        handoff = db.execute(
            select(CoverageReviewHandoff)
            .where(CoverageReviewHandoff.id == handoff_id)
            .with_for_update()
        ).scalar_one_or_none()

        if handoff is None:
            raise LookupError("Handoff not found.")

        if handoff.status != "pending":
            raise ReviewConflictError(
                "This handoff has already been reviewed."
            )

        workflow = db.execute(
            select(CoverageWorkflow)
            .where(
                CoverageWorkflow.id == handoff.workflow_id
            )
            .with_for_update()
        ).scalar_one_or_none()

        if workflow is None:
            raise LookupError("Workflow not found.")

        if workflow.status != "needs_review":
            raise ReviewConflictError(
                "Workflow is not awaiting review."
            )

        handoff_statuses = {
            ReviewDecision.APPROVE: "approved",
            ReviewDecision.REQUEST_CHANGES: "changes_requested",
            ReviewDecision.REJECT: "rejected",
        }

        
        if workflow.current_step == "insurance_review":
            workflow_states = {
                ReviewDecision.APPROVE: (
                    "running", "insurance_review_complete"
                ),
                ReviewDecision.REQUEST_CHANGES: (
                    "needs_review", "awaiting_customer"
                ),
                ReviewDecision.REJECT: (
                    "rejected", "closed"
                ),
            }
        else:
            workflow_states = {
                ReviewDecision.APPROVE: (
                    "running", "policy_review"
                ),
                ReviewDecision.REQUEST_CHANGES: (
                    "needs_review", "awaiting_customer"
                ),
                ReviewDecision.REJECT: (
                    "rejected", "closed"
                ),
            }

        handoff.status = handoff_statuses[decision]
        handoff.reviewer_id = reviewer_id
        handoff.reviewer_notes = notes
        handoff.reviewed_at = datetime.now(timezone.utc)

        new_status, new_step = workflow_states[decision]
        workflow.status = new_status
        workflow.current_step = new_step

        db.add(
            CoverageWorkflowEvent(
                workflow_id=workflow.id,
                event_type="handoff_reviewed",
                actor=reviewer_id,
                details={
                    "handoff_id": str(handoff.id),
                    "decision": decision.value,
                    "notes": notes,
                    "handoff_status": handoff.status,
                    "workflow_status": new_status,
                },
            )
        )

        workflow_id = workflow.id
        final_handoff_status = handoff.status

        db.commit()

        return {
            "handoff_id": str(handoff_id),
            "workflow_id": str(workflow_id),
            "decision": decision.value,
            "handoff_status": final_handoff_status,
            "workflow_status": new_status,
            "current_step": new_step,
            "reviewer_id": reviewer_id,
        }

    except Exception:
        db.rollback()
        raise