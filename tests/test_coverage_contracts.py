
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.coverage.contracts import (
    AgentHandoff,
    EvidenceReference,
    Finding,
    WorkflowStatus,
)


def test_handoff_default_status():
    handoff = AgentHandoff(
        workflow_id=uuid4(),
        from_agent="onboarding",
        to_agent="policy",
        summary="Customer intake complete",
    )

    assert handoff.status == WorkflowStatus.PENDING
    assert handoff.findings == []


def test_evidence_requires_positive_page():
    with pytest.raises(ValidationError):
        EvidenceReference(
            document_id=uuid4(),
            page=0,
            excerpt="Coverage limit",
        )


def test_handoff_preserves_findings():
    finding = Finding(
        field_name="general_liability_limit",
        observed_value="$1,000,000",
        requirement="$2,000,000",
        needs_review=True,
    )

    handoff = AgentHandoff(
        workflow_id=uuid4(),
        from_agent="coverage",
        to_agent="evaluation",
        summary="Limit requires review",
        findings=[finding],
    )

    assert len(handoff.findings) == 1
    assert handoff.findings[0].needs_review is True