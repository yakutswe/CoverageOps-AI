
import asyncio
from datetime import date

from app.coverage.agents.policy_agents import (
    PolicyAgent,
    CoverageComparisonAgent,
    PolicyEvaluationAgent,
)
from app.coverage.orchestration import (
    AgentRegistry,
    CoverageOrchestrator,
)


def make_orchestrator():
    registry = AgentRegistry()

    registry.register(PolicyAgent())
    registry.register(CoverageComparisonAgent())
    registry.register(PolicyEvaluationAgent())

    return CoverageOrchestrator(registry)


def make_payload(policy_limit="1000000"):
    return {
        "policy": {
            "policy_number": "NS-DEMO-001",
            "insured_name": "Northstar Logistics",
            "carrier": "Fictional Insurance Co.",
            "effective_date": date(2026, 10, 1).isoformat(),
            "expiration_date": date(2027, 10, 1).isoformat(),
            "limits": [
                {
                    "coverage_type": "general_liability",
                    "limit_amount": policy_limit,
                    "currency": "USD",
                    "evidence": {
                        "document_id": "policy-001",
                        "page": 1,
                        "excerpt": "General liability occurrence limit",
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
                    "document_id": "requirements-001",
                    "page": 1,
                    "excerpt": "Minimum required limit: $2,000,000",
                },
            }
        ],
    }


async def run_pipeline(payload):
    return await make_orchestrator().run_sequence(
        customer_id="northstar-demo",
        steps=[
            "policy",
            "coverage_comparison",
            "policy_evaluation",
        ],
        initial_payload=payload,
    )


def test_three_agents_run_in_order():
    results = asyncio.run(
        run_pipeline(make_payload())
    )

    assert [item.agent_name for item in results] == [
        "policy",
        "coverage_comparison",
        "policy_evaluation",
    ]

    assert results[0].status == "completed"
    assert results[1].status == "completed"
    assert results[2].status == "needs_review"

    assert len({
        item.workflow_id for item in results
    }) == 1


def test_discrepancy_requires_human_review():
    results = asyncio.run(
        run_pipeline(make_payload("1000000"))
    )

    finding = results[1].output["findings"][0]

    assert finding["status"] == "below_requirement"
    assert finding["policy_limit"] == "1000000"
    assert finding["required_limit"] == "2000000"

    assert results[2].output["review_required"] is True
    assert results[2].output["flagged_count"] == 1


def test_numeric_limit_passes():
    results = asyncio.run(
        run_pipeline(make_payload("3000000"))
    )

    finding = results[1].output["findings"][0]

    assert finding["status"] == "limit_meets_minimum"
    assert results[2].status == "completed"
    assert results[2].output["review_required"] is False


def test_invalid_policy_stops_pipeline():
    payload = make_payload()
    payload["policy"]["expiration_date"] = "2026-09-01"

    results = asyncio.run(run_pipeline(payload))

    assert len(results) == 1
    assert results[0].agent_name == "policy"
    assert results[0].status == "needs_review"
    assert "validation_error" in results[0].output


def test_agents_are_registered():
    orchestrator = make_orchestrator()

    assert orchestrator.registry.list_agents() == [
        "coverage_comparison",
        "policy",
        "policy_evaluation",
    ]