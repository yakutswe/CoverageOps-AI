
import asyncio
import os
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.coverage.services.onboarding import (
    create_customer_workflow,
)
from app.coverage.services.workflow import execute_onboarding
from app.coverage.services.review import (
    review_handoff,
    ReviewDecision,
    ReviewConflictError,
)
from app.coverage.services.resubmission import (
    resubmit_customer_intake,
)
from app.db.models import (
    CoverageCustomer,
    CoverageWorkflow,
    CoverageWorkflowEvent,
    CoverageReviewHandoff,
)


load_dotenv(
    Path(__file__).resolve().parents[1] / ".env"
)


@pytest.fixture
def db():
    source_url = os.environ["DATABASE_URL"]
    test_url = make_url(source_url).set(
        database="agentlab_test"
    )

    # Never write integration-test data to development DB.
    if test_url.database != "agentlab_test":
        raise RuntimeError("Unsafe integration-test database.")

    if test_url.drivername != "postgresql+psycopg":
        raise RuntimeError("Expected PostgreSQL/psycopg.")

    engine = create_engine(test_url)
    session = Session(engine)

    # Track this test's customer using a unique marker.
    marker = f"integration-{uuid.uuid4()}"

    try:
        yield session, marker
    finally:
        session.rollback()

        # Delete only records created by this test.
        customers = session.scalars(
            select(CoverageCustomer).where(
                CoverageCustomer.company_name == marker
            )
        ).all()

        for customer in customers:
            workflows = session.scalars(
                select(CoverageWorkflow).where(
                    CoverageWorkflow.customer_id == customer.id
                )
            ).all()

            for workflow in workflows:
                session.query(
                    CoverageReviewHandoff
                ).filter_by(
                    workflow_id=workflow.id
                ).delete()

                session.query(
                    CoverageWorkflowEvent
                ).filter_by(
                    workflow_id=workflow.id
                ).delete()

                session.delete(workflow)

            session.flush()
            session.delete(customer)

        session.commit()
        session.close()
        engine.dispose()


def create_case(db, marker):
    result = create_customer_workflow(
        db=db,
        company_name=marker,
        industry="Logistics",
    )
    return uuid.UUID(result["workflow_id"])


def test_customer_and_audit_persist(db):
    session, marker = db
    workflow_id = create_case(session, marker)

    session.expire_all()

    workflow = session.get(
        CoverageWorkflow, workflow_id
    )

    assert workflow is not None
    assert workflow.status == "pending"

    count = session.scalar(
        select(func.count())
        .select_from(CoverageWorkflowEvent)
        .where(
            CoverageWorkflowEvent.workflow_id
            == workflow_id
        )
    )

    assert count == 1


def test_missing_intake_creates_handoff(db):
    session, marker = db
    workflow_id = create_case(session, marker)

    result = asyncio.run(
        execute_onboarding(
            db=session,
            workflow_id=workflow_id,
            intake_payload={
                "company_name": marker
            },
        )
    )

    assert result["status"] == "needs_review"
    assert result["current_step"] == "human_review"
    assert result["handoff_id"] is not None

    handoff = session.get(
        CoverageReviewHandoff,
        uuid.UUID(result["handoff_id"]),
    )

    assert handoff is not None
    assert handoff.status == "pending"
    assert handoff.findings[0]["field_name"] == "industry"


def test_duplicate_review_is_rejected(db):
    session, marker = db
    workflow_id = create_case(session, marker)

    result = asyncio.run(
        execute_onboarding(
            session,
            workflow_id,
            {"company_name": marker},
        )
    )

    handoff_id = uuid.UUID(result["handoff_id"])

    review_handoff(
        db=session,
        handoff_id=handoff_id,
        reviewer_id="advisor-test-001",
        decision=ReviewDecision.REQUEST_CHANGES,
        notes="Industry classification required.",
    )

    with pytest.raises(ReviewConflictError):
        review_handoff(
            db=session,
            handoff_id=handoff_id,
            reviewer_id="advisor-test-002",
            decision=ReviewDecision.APPROVE,
            notes="Duplicate decision attempt.",
        )

    session.expire_all()

    handoff = session.get(
        CoverageReviewHandoff, handoff_id
    )

    assert handoff.status == "changes_requested"
    assert handoff.reviewer_id == "advisor-test-001"

    event_count = session.scalar(
        select(func.count())
        .select_from(CoverageWorkflowEvent)
        .where(
            CoverageWorkflowEvent.workflow_id
            == workflow_id
        )
    )

    assert event_count == 3


def test_resubmission_resumes_workflow(db):
    session, marker = db
    workflow_id = create_case(session, marker)

    result = asyncio.run(
        execute_onboarding(
            session,
            workflow_id,
            {"company_name": marker},
        )
    )

    review_handoff(
        db=session,
        handoff_id=uuid.UUID(result["handoff_id"]),
        reviewer_id="advisor-test-001",
        decision=ReviewDecision.REQUEST_CHANGES,
        notes="Please confirm industry.",
    )

    response = asyncio.run(
        resubmit_customer_intake(
            db=session,
            workflow_id=workflow_id,
            industry="Logistics",
        )
    )

    assert response["status"] == "running"
    assert response["current_step"] == "policy_review"
    assert response["intake_complete"] is True

    session.expire_all()

    workflow = session.get(
        CoverageWorkflow, workflow_id
    )

    assert workflow.status == "running"

    event_count = session.scalar(
        select(func.count())
        .select_from(CoverageWorkflowEvent)
        .where(
            CoverageWorkflowEvent.workflow_id
            == workflow_id
        )
    )

    assert event_count == 4