
from app.coverage.orchestration import (
    AgentTask,
    AgentResult,
)


class OnboardingAgent:
    name = "onboarding"

    async def execute(self, task: AgentTask) -> AgentResult:
        required = ["company_name", "industry"]

        missing = [
            field
            for field in required
            if not task.payload.get(field)
        ]

        return AgentResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            customer_id=task.customer_id,
            agent_name=self.name,
            status=(
                "needs_review" if missing else "completed"
            ),
            output={
                "missing_fields": missing,
                "intake_complete": not missing,
            },
        )


class EvaluationAgent:
    name = "evaluation"

    async def execute(self, task: AgentTask) -> AgentResult:
        onboarding = task.payload.get("onboarding", {})

        valid = onboarding.get("intake_complete") is True

        return AgentResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            customer_id=task.customer_id,
            agent_name=self.name,
            status="completed",
            output={
                "passed": valid,
                "checks": {
                    "onboarding_complete": valid,
                },
            },
        )
