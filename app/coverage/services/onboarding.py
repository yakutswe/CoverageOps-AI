
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import (
    CoverageCustomer,
    CoverageWorkflow,
    CoverageWorkflowEvent,
)


def create_customer_workflow(
    db: Session,
    company_name: str,
    industry: str,
) -> dict:
    """
    Create a customer and onboarding workflow
    in a single database transaction.
    """

    company_name = company_name.strip()
    industry = industry.strip()

    if not company_name:
        raise ValueError("Company name cannot be empty.")

    if not industry:
        raise ValueError("Industry cannot be empty.")

    try:
        customer = CoverageCustomer(
            company_name=company_name,
            industry=industry,
        )
        db.add(customer)
        db.flush()

        workflow = CoverageWorkflow(
            customer_id=customer.id,
            status="pending",
            current_step="intake",
        )
        db.add(workflow)
        db.flush()

        event = CoverageWorkflowEvent(
            workflow_id=workflow.id,
            event_type="workflow_created",
            actor="system",
            details={
                "company_name": company_name,
                "industry": industry,
            },
        )
        db.add(event)

        customer_id = customer.id
        workflow_id = workflow.id

        # Commit all three records together.
        db.commit()

        return {
            "customer_id": str(customer_id),
            "workflow_id": str(workflow_id),
            "status": "pending",
            "current_step": "intake",
        }

    except Exception:
        db.rollback()
        raise


def get_workflow_events(
    db: Session,
    workflow_id: UUID,
) -> list[CoverageWorkflowEvent]:
    return (
        db.query(CoverageWorkflowEvent)
        .filter(
            CoverageWorkflowEvent.workflow_id
            == workflow_id
        )
        .order_by(
            CoverageWorkflowEvent.created_at,
            CoverageWorkflowEvent.id,
        )
        .all()
    )