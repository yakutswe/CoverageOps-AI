
from uuid import UUID

from sqlalchemy.orm import Session

from app.coverage.agents.prototypes import OnboardingAgent
from app.coverage.orchestration import AgentTask
from app.db.models import (
    CoverageWorkflow,
    CoverageWorkflowEvent,
    CoverageReviewHandoff,
)


async def execute_onboarding(
    db: Session,
    workflow_id: UUID,
    intake_payload: dict,
) -> dict:
    try:
        workflow = (
            db.query(CoverageWorkflow)
            .filter(CoverageWorkflow.id == workflow_id)
            .with_for_update()
            .one_or_none()
        )

        if workflow is None:
            raise ValueError("Workflow not found")

        if workflow.status != "pending":
            raise ValueError(
                "Workflow is not pending"
            )

        task = AgentTask(
            workflow_id=workflow_id,
            customer_id=str(workflow.customer_id),
            agent_name="onboarding",
            payload=intake_payload,
        )

        agent = OnboardingAgent()
        result = await agent.execute(task)

        if result.status not in (
            "completed",
            "needs_review",
        ):
            raise ValueError(
                "Unexpected onboarding agent status"
            )

        handoff_id = None

        if result.status == "needs_review":
            missing = result.output["missing_fields"]

            handoff = CoverageReviewHandoff(
                workflow_id=workflow_id,
                from_agent="onboarding",
                assigned_to="risk_advisor_queue",
                status="pending",
                summary=(
                    "Customer onboarding requires "
                    "additional information."
                ),
                findings=[
                    {
                        "field_name": field,
                        "issue": "missing_information",
                    }
                    for field in missing
                ],
            )

            db.add(handoff)
            db.flush()

            handoff_id = str(handoff.id)
            workflow.status = "needs_review"
            workflow.current_step = "human_review"

        else:
            workflow.status = "running"
            workflow.current_step = "policy_review"

        event = CoverageWorkflowEvent(
            workflow_id=workflow_id,
            event_type="onboarding_evaluated",
            actor="onboarding",
            details={
                "task_id": str(task.task_id),
                "agent_status": result.status,
                "output": result.output,
                "handoff_id": handoff_id,
            },
        )

        db.add(event)
        db.commit()

        return {
            "workflow_id": str(workflow_id),
            "agent": "onboarding",
            "status": workflow.status,
            "current_step": workflow.current_step,
            "result": result.output,
            "handoff_id": handoff_id,
        }

    except Exception:
        db.rollback()
        raise