
import asyncio
import os
import uuid
from datetime import date
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.coverage.services.policy_review import (
    PolicyReviewConflictError,
    execute_policy_review,
)
from app.db.models import (
    CoverageCustomer,
    CoverageWorkflow,
    CoverageWorkflowEvent,
    CoverageReviewHandoff,
)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@pytest.fixture
def policy_case():
    source_url = os.environ["DATABASE_URL"]
    test_url = make_url(source_url).set(
        database="agentlab_test"
    )

    if (
        test_url.database != "agentlab_test"
        or test_url.drivername != "postgresql+psycopg"
    ):
        raise RuntimeError("Unsafe test database configuration.")

    engine = create_engine(test_url)
    session = Session(engine)

    customer_id = uuid.uuid4()
    workflow_id = uuid.uuid4()

    try:
        customer = CoverageCustomer(
            id=customer_id,
            company_name=f"Policy Test {customer_id}",
            industry="Logistics",
        )
        workflow = CoverageWorkflow(
            id=workflow_id,
            customer_id=customer_id,
            status="running",
            current_step="policy_review",
        )

        session.add_all([customer, workflow])
        session.commit()

        yield session, workflow_id

    finally:
        try:
            session.rollback()

            session.execute(
                delete(CoverageReviewHandoff).where(
                    CoverageReviewHandoff.workflow_id
                    == workflow_id
                )
            )
            session.execute(
                delete(CoverageWorkflowEvent).where(
                    CoverageWorkflowEvent.workflow_id
                    == workflow_id
                )
            )
            session.execute(
                delete(CoverageWorkflow).where(
                    CoverageWorkflow.id == workflow_id
                )
            )
            session.execute(
                delete(CoverageCustomer).where(
                    CoverageCustomer.id == customer_id
                )
            )
            session.commit()
        finally:
            session.close()
            engine.dispose()


def make_payload(limit="1000000"):
    return {
        "policy": {
            "policy_number": "TEST-GL-001",
            "insured_name": "Northstar Logistics",
            "carrier": "Fictional Insurance Co.",
            "effective_date": date(2026, 10, 1).isoformat(),
            "expiration_date": date(2027, 10, 1).isoformat(),
            "limits": [
                {
                    "coverage_type": "general_liability",
                    "limit_amount": limit,
                    "currency": "USD",
                    "evidence": {
                        "document_id": "test-policy",
                        "page": 1,
                        "excerpt": "Occurrence limit",
                    },
                }
            ],
        },
        "requirements": [
            {
                "coverage_type": "general_liability",
                "minimum_limit": "2000000",
                "currency": "USD",
                "evidence": {
                    "document_id": "test-requirements",
                    "page": 1,
                    "excerpt": "Minimum occurrence limit",
                },
            }
        ],
    }


def test_discrepancy_creates_persistent_handoff(policy_case):
    session, workflow_id = policy_case

    result = asyncio.run(
        execute_policy_review(
            session, workflow_id, make_payload()
        )
    )

    assert result["status"] == "needs_review"
    assert result["current_step"] == "insurance_review"
    assert result["review_required"] is True
    assert result["handoff_id"] is not None
    assert len(result["agent_results"]) == 3

    session.expire_all()

    handoff = session.get(
        CoverageReviewHandoff,
        uuid.UUID(result["handoff_id"]),
    )

    assert handoff.status == "pending"
    assert handoff.assigned_to == "insurance_advisor"
    assert handoff.findings[0]["status"] == "below_requirement"

    events = session.scalars(
        select(CoverageWorkflowEvent).where(
            CoverageWorkflowEvent.workflow_id == workflow_id
        )
    ).all()

    assert len(events) == 4
    assert sum(
        event.event_type == "insurance_agent_completed"
        for event in events
    ) == 3


def test_numeric_pass_persists_without_handoff(policy_case):
    session, workflow_id = policy_case

    result = asyncio.run(
        execute_policy_review(
            session,
            workflow_id,
            make_payload("3000000"),
        )
    )

    assert result["review_required"] is False
    assert result["handoff_id"] is None
    assert result["status"] == "running"
    assert result["current_step"] == "policy_review_complete"

    handoff_count = session.scalar(
        select(func.count())
        .select_from(CoverageReviewHandoff)
        .where(
            CoverageReviewHandoff.workflow_id == workflow_id
        )
    )

    assert handoff_count == 0

    event_count = session.scalar(
        select(func.count())
        .select_from(CoverageWorkflowEvent)
        .where(
            CoverageWorkflowEvent.workflow_id == workflow_id
        )
    )

    assert event_count == 3


def test_duplicate_policy_execution_is_rejected(policy_case):
    session, workflow_id = policy_case

    asyncio.run(
        execute_policy_review(
            session, workflow_id, make_payload()
        )
    )

    with pytest.raises(PolicyReviewConflictError):
        asyncio.run(
            execute_policy_review(
                session, workflow_id, make_payload()
            )
        )

    handoff_count = session.scalar(
        select(func.count())
        .select_from(CoverageReviewHandoff)
        .where(
            CoverageReviewHandoff.workflow_id == workflow_id
        )
    )

    assert handoff_count == 1
    

def test_insurance_approval_transition(policy_case):
    from uuid import UUID

    from app.coverage.services.review import (
        review_handoff,
        ReviewDecision,
    )

    session, workflow_id = policy_case

    result = asyncio.run(
        execute_policy_review(
            session,
            workflow_id,
           make_payload("1000000"),
        )
    )

    reviewed = review_handoff(
        db=session,
        handoff_id=UUID(result["handoff_id"]),
        reviewer_id="insurance-advisor-test",
        decision=ReviewDecision.APPROVE,
        notes="Reviewed the flagged discrepancy.",
    )

    assert reviewed["workflow_status"] == "running"
    assert reviewed["current_step"] == "insurance_review_complete"
    assert reviewed["handoff_status"] == "approved"
