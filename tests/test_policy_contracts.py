
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.coverage.policy_contracts import (
    CoverageType,
    PolicyEvidence,
    CoverageLimit,
    InsurancePolicy,
)


def sample_evidence():
    return PolicyEvidence(
        document_id="northstar-policy-001",
        page=2,
        excerpt="General liability limit: $1,000,000",
    )


def test_policy_evidence():
    evidence = sample_evidence()

    assert evidence.document_id == "northstar-policy-001"
    assert evidence.page == 2


def test_rejects_invalid_page():
    with pytest.raises(ValidationError):
        PolicyEvidence(
            document_id="test",
            page=0,
            excerpt="Invalid evidence",
        )


def test_coverage_limit_uses_decimal():
    limit = CoverageLimit(
        coverage_type=CoverageType.GENERAL_LIABILITY,
        limit_amount="1000000.00", # pyright: ignore[reportArgumentType]
        evidence=sample_evidence(),
    )

    assert limit.limit_amount == Decimal("1000000.00")


def test_rejects_negative_limit():
    with pytest.raises(ValidationError):
        CoverageLimit(
            coverage_type=CoverageType.GENERAL_LIABILITY,
            limit_amount=Decimal("-100"),
            evidence=sample_evidence(),
        )


def test_rejects_invalid_policy_dates():
    with pytest.raises(ValidationError):
        InsurancePolicy(
            policy_number="NS-001",
            insured_name="Northstar Logistics",
            carrier="Demo Insurance",
            effective_date=date(2026, 10, 1),
            expiration_date=date(2026, 9, 30),
        )