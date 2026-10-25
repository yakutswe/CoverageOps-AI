
from pydantic import ValidationError

from app.coverage.orchestration import AgentTask, AgentResult
from app.coverage.policy_contracts import (
    InsurancePolicy,
    CoverageRequirement,
    CoverageComparison,
)
from app.coverage.services.comparison import compare_policy


def make_result(task, agent_name, status, output):
    return AgentResult(
        task_id=task.task_id,
        workflow_id=task.workflow_id,
        customer_id=task.customer_id,
        agent_name=agent_name,
        status=status,
        output=output,
    )


class PolicyAgent:
    name = "policy"

    async def execute(self, task: AgentTask) -> AgentResult:
        try:
            policy = InsurancePolicy.model_validate(
                task.payload["policy"]
            )
        except (KeyError, ValidationError) as exc:
            return make_result(
                task,
                self.name,
                "needs_review",
                {"validation_error": str(exc)},
            )

        return make_result(
            task,
            self.name,
            "completed",
            {
                "policy": policy.model_dump(mode="json"),
                "validated": True,
            },
        )


class CoverageComparisonAgent:
    name = "coverage_comparison"

    async def execute(self, task: AgentTask) -> AgentResult:
        try:
            policy_data = task.payload["policy"]["policy"]
            policy = InsurancePolicy.model_validate(
                policy_data
            )

            requirements = [
                CoverageRequirement.model_validate(item)
                for item in task.payload["requirements"]
            ]

            if not requirements:
                raise ValueError(
                    "At least one coverage requirement is needed."
                )

        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            return make_result(
                task,
                self.name,
                "needs_review",
                {"validation_error": str(exc)},
            )

        findings = compare_policy(policy, requirements)

        return make_result(
            task,
            self.name,
            "completed",
            {
                "findings": [
                    item.model_dump(mode="json")
                    for item in findings
                ],
                "total_findings": len(findings),
            },
        )


class PolicyEvaluationAgent:
    name = "policy_evaluation"

    async def execute(self, task: AgentTask) -> AgentResult:
        comparison = task.payload.get(
            "coverage_comparison", {}
        )

        try:
            findings = [
                CoverageComparison.model_validate(item)
                for item in comparison["findings"]
            ]

            if not findings:
                raise ValueError("No comparison findings supplied.")

        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            return make_result(
                task,
                self.name,
                "needs_review",
                {"validation_error": str(exc)},
            )

        valid_evidence = all(
            finding.requirement_evidence is not None
            and (
                finding.status == "missing_information"
                or finding.policy_evidence is not None
            )
            for finding in findings
        )

        flagged_statuses = {
            "below_requirement",
            "missing_information",
            "needs_review",
        }

        flagged = [
            finding
            for finding in findings
            if finding.status in flagged_statuses
        ]

        review_required = (
            bool(flagged) or not valid_evidence
        )

        return make_result(
            task,
            self.name,
            "needs_review" if review_required else "completed",
            {
                "evidence_complete": valid_evidence,
                "review_required": review_required,
                "flagged_count": len(flagged),
                "finding_statuses": [
                    finding.status for finding in findings
                ],
            },
        )