
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coverage.agents.prototypes import OnboardingAgent
from app.coverage.orchestration import AgentTask
from app.db.models import (
    CoverageCustomer,
    CoverageWorkflow,
    CoverageReviewHandoff,
    CoverageWorkflowEvent,
)


class ResubmissionConflictError(Exception):
    pass


async def resubmit_customer_intake(
    db: Session,
    workflow_id: UUID,
    industry: str,
) -> dict:
    industry = industry.strip()

    if not industry:
        raise ValueError("Industry is required.")

    try:
        workflow = db.execute(
            select(CoverageWorkflow)
            .where(CoverageWorkflow.id == workflow_id)
            .with_for_update()
        ).scalar_one_or_none()

        if workflow is None:
            raise LookupError("Workflow not found.")

        if (
            workflow.status != "needs_review"
            or workflow.current_step != "awaiting_customer"
        ):
            raise ResubmissionConflictError(
                "Workflow is not awaiting customer clarification."
            )

        handoff = db.execute(
            select(CoverageReviewHandoff)
            .where(
                CoverageReviewHandoff.workflow_id == workflow_id,
                CoverageReviewHandoff.status == "changes_requested",
            )
            .order_by(CoverageReviewHandoff.created_at.desc())
        ).scalars().first()

        if handoff is None:
            raise ResubmissionConflictError(
                "No requested changes exist for this workflow."
            )

        customer = db.get(
            CoverageCustomer,
            workflow.customer_id,
        )

        if customer is None:
            raise LookupError("Customer not found.")

        task = AgentTask(
            workflow_id=workflow_id,
            customer_id=str(customer.id),
            agent_name="onboarding",
            payload={
                "company_name": customer.company_name,
                "industry": industry,
            },
        )

        result = await OnboardingAgent().execute(task)

        if (
            result.status != "completed"
            or result.output.get("intake_complete") is not True
        ):
            raise ResubmissionConflictError(
                "Corrected intake did not pass validation."
            )

        # Reconcile the verified correction with
        # the customer master record.
        previous_industry = customer.industry
        customer.industry = industry

        workflow.status = "running"
        workflow.current_step = "policy_review"

        db.add(
            CoverageWorkflowEvent(
                workflow_id=workflow_id,
                event_type="customer_intake_resubmitted",
                actor="customer_demo",
                details={
                    "task_id": str(task.task_id),
                    "previous_industry": previous_industry,
                    "submitted_industry": industry,
                    "agent_status": result.status,
                    "source_handoff_id": str(handoff.id),
                },
            )
        )

        db.commit()

        return {
            "workflow_id": str(workflow_id),
            "status": "running",
            "current_step": "policy_review",
            "intake_complete": True,
            "source_handoff_id": str(handoff.id),
        }

    except Exception:
        db.rollback()
        raise