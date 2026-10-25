
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.coverage.agents.prototypes import (  # type: ignore[reportMissingImports]
    OnboardingAgent,
    EvaluationAgent,
)
from app.coverage.orchestration import (
    AgentRegistry,
    AgentTask,
    CoverageOrchestrator,
)


def make_orchestrator():
    registry = AgentRegistry()
    registry.register(OnboardingAgent())  # type: ignore[arg-type]
    registry.register(EvaluationAgent())  # type: ignore[arg-type]
    return CoverageOrchestrator(registry)


def test_agents_registered():
    orchestrator = make_orchestrator()

    assert orchestrator.registry.list_agents() == [
        "evaluation",
        "onboarding",
    ]


def test_duplicate_agent_rejected():
    registry = AgentRegistry()
    registry.register(OnboardingAgent())  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        registry.register(OnboardingAgent())  # type: ignore[arg-type]


def test_independent_agent_execution():
    orchestrator = make_orchestrator()

    task = AgentTask(
        agent_name="onboarding",
        customer_id="northstar",
        payload={
            "company_name": "Northstar Logistics",
            "industry": "logistics",
        },
    )

    result = asyncio.run(
        orchestrator.run_agent(task)
    )

    assert result.status == "completed"
    assert result.output["intake_complete"] is True


def test_agents_work_together():
    orchestrator = make_orchestrator()

    results = asyncio.run(
        orchestrator.run_sequence(
            customer_id="northstar",
            steps=["onboarding", "evaluation"],
            initial_payload={
                "company_name": "Northstar Logistics",
                "industry": "logistics",
            },
        )
    )

    assert len(results) == 2
    assert results[0].agent_name == "onboarding"
    assert results[1].agent_name == "evaluation"
    assert results[1].output["passed"] is True


def test_incomplete_intake_stops_workflow():
    orchestrator = make_orchestrator()

    results = asyncio.run(
        orchestrator.run_sequence(
            customer_id="northstar",
            steps=["onboarding", "evaluation"],
            initial_payload={
                "company_name": "Northstar Logistics",
            },
        )
    )

    assert len(results) == 1
    assert results[0].status == "needs_review"
    assert results[0].output["missing_fields"] == [
        "industry"
    ]