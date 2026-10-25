
from datetime import date
from decimal import Decimal

from app.coverage.policy_contracts import (
    CoverageLimit,
    CoverageRequirement,
    CoverageType,
    InsurancePolicy,
    PolicyEvidence,
)
from app.coverage.services.comparison import compare_policy


def evidence(document, excerpt):
    return PolicyEvidence(
        document_id=document,
        page=1,
        excerpt=excerpt,
    )


def make_policy(limit="1000000"):
    return InsurancePolicy(
        policy_number="NS-DEMO-001",
        insured_name="Northstar Logistics",
        carrier="Fictional Insurance Co.",
        effective_date=date(2026, 10, 1),
        expiration_date=date(2027, 10, 1),
        limits=[
            CoverageLimit(
                coverage_type=CoverageType.GENERAL_LIABILITY,
                limit_amount=Decimal(limit),
                evidence=evidence(
                    "policy-001",
                    "General liability limit stated",
                ),
            )
        ],
    )


def requirement():
    return CoverageRequirement(
        coverage_type=CoverageType.GENERAL_LIABILITY,
        minimum_limit="2000000",
        evidence=evidence(
            "landlord-requirements-001",
            "General liability minimum: $2,000,000",
        ),
    )


def test_detects_limit_discrepancy():
    result = compare_policy(
        make_policy(),
        [requirement()],
    )[0]

    assert result.status == "below_requirement"
    assert result.policy_limit == 1000000
    assert result.required_limit == 2000000


def test_limit_meets_numeric_minimum():
    result = compare_policy(
        make_policy("3000000"),
        [requirement()],
    )[0]

    assert result.status == "limit_meets_minimum"


def test_preserves_both_evidence_sources():
    result = compare_policy(
        make_policy(),
        [requirement()],
    )[0]

    assert result.policy_evidence is not None
    assert result.policy_evidence.document_id == "policy-001"
    assert result.requirement_evidence is not None
    assert (
        result.requirement_evidence.document_id
        == "landlord-requirements-001"
    )


def test_missing_coverage_information():
    policy = make_policy()
    policy.limits = []

    result = compare_policy(
        policy,
        [requirement()],
    )[0]

    assert result.status == "missing_information"
    assert result.policy_evidence is None


def test_currency_mismatch_requires_review():
    policy = make_policy()
    policy.limits[0].currency = "EUR"

    result = compare_policy(
        policy,
        [requirement()],
    )[0]

    assert result.status == "needs_review"


def test_duplicate_limits_require_review():
    policy = make_policy()
    policy.limits.append(policy.limits[0].model_copy())

    result = compare_policy(
        policy,
        [requirement()],
    )[0]

    assert result.status == "needs_review"