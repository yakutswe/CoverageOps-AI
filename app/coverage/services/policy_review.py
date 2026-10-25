
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coverage.agents.policy_agents import (
    PolicyAgent,
    CoverageComparisonAgent,
    PolicyEvaluationAgent,
)
from app.coverage.orchestration import (
    AgentRegistry,
    CoverageOrchestrator,
)
from app.db.models import (
    CoverageWorkflow,
    CoverageWorkflowEvent,
    CoverageReviewHandoff,
)


class PolicyReviewConflictError(Exception):
    pass


def build_policy_orchestrator() -> CoverageOrchestrator:
    registry = AgentRegistry()
    registry.register(PolicyAgent())
    registry.register(CoverageComparisonAgent())
    registry.register(PolicyEvaluationAgent())
    return CoverageOrchestrator(registry)


async def execute_policy_review(
    db: Session,
    workflow_id: UUID,
    payload: dict,
) -> dict:
    """
    Execute structured insurance analysis and persist
    all agent results and any specialist handoff.

    This does not perform insurance underwriting
    or independently verify source documents.
    """

    if not isinstance(payload, dict):
        raise ValueError("Policy review payload must be an object.")

    # Check eligibility before doing agent work.
    workflow = db.get(CoverageWorkflow, workflow_id)

    if workflow is None:
        raise LookupError("Workflow not found.")

    if (
        workflow.status != "running"
        or workflow.current_step != "policy_review"
    ):
        raise PolicyReviewConflictError(
            "Workflow is not ready for policy review."
        )

    customer_id = str(workflow.customer_id)

    # Release the preliminary read transaction.
    db.rollback()

    orchestrator = build_policy_orchestrator()

    results = await orchestrator.run_sequence(
        customer_id=customer_id,
        workflow_id=workflow_id,
        steps=[
            "policy",
            "coverage_comparison",
            "policy_evaluation",
        ],
        initial_payload=payload,
    )

    if not results:
        raise RuntimeError("No agent results were produced.")

    review_required = any(
        result.status != "completed"
        for result in results
    )

    try:
        # Recheck state under a database lock before saving.
        workflow = db.execute(
            select(CoverageWorkflow)
            .where(CoverageWorkflow.id == workflow_id)
            .with_for_update()
        ).scalar_one_or_none()

        if workflow is None:
            raise LookupError("Workflow not found.")

        if (
            workflow.status != "running"
            or workflow.current_step != "policy_review"
        ):
            raise PolicyReviewConflictError(
                "Workflow state changed during analysis."
            )

        existing_handoff = db.execute(
            select(CoverageReviewHandoff.id)
            .where(
                CoverageReviewHandoff.workflow_id == workflow_id,
                CoverageReviewHandoff.status == "pending",
            )
        ).first()

        if existing_handoff is not None:
            raise PolicyReviewConflictError(
                "A pending review handoff already exists."
            )

        for result in results:
            if result.workflow_id != workflow_id:
                raise ValueError(
                    "Agent result has an incorrect workflow ID."
                )

            db.add(
                CoverageWorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="insurance_agent_completed",
                    actor=result.agent_name,
                    details=result.model_dump(mode="json"),
                )
            )

        comparison_result = next(
            (
                result
                for result in results
                if result.agent_name == "coverage_comparison"
            ),
            None,
        )

        findings = (
            comparison_result.output.get("findings", [])
            if comparison_result is not None
            else []
        )

        handoff_id = None

        if review_required:
            handoff = CoverageReviewHandoff(
                workflow_id=workflow_id,
                from_agent=results[-1].agent_name,
                assigned_to="insurance_advisor",
                status="pending",
                summary=(
                    "Insurance policy analysis requires "
                    "specialist review."
                ),
                findings=findings,
            )

            db.add(handoff)
            db.flush()
            handoff_id = str(handoff.id)

            workflow.status = "needs_review"
            workflow.current_step = "insurance_review"

            db.add(
                CoverageWorkflowEvent(
                    workflow_id=workflow_id,
                    event_type="insurance_review_requested",
                    actor="system",
                    details={
                        "handoff_id": handoff_id,
                        "finding_count": len(findings),
                        "reason": (
                            "Agent analysis requires human review."
                        ),
                    },
                )
            )
        else:
            workflow.status = "running"
            workflow.current_step = "policy_review_complete"

        db.commit()

        return {
            "workflow_id": str(workflow_id),
            "status": workflow.status,
            "current_step": workflow.current_step,
            "review_required": review_required,
            "handoff_id": handoff_id,
            "agent_results": [
                result.model_dump(mode="json")
                for result in results
            ],
        }

    except Exception:
        db.rollback()
        raise