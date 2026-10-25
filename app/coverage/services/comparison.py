from app.coverage.policy_contracts import (
    InsurancePolicy,
    CoverageRequirement,
    CoverageComparison,
)


def compare_policy(
    policy: InsurancePolicy,
    requirements: list[CoverageRequirement],
) -> list[CoverageComparison]:
    """Compare documented numeric limits with stated requirements."""
    results = []

    for requirement in requirements:
        matches = [
            limit
            for limit in policy.limits
            if limit.coverage_type == requirement.coverage_type
        ]

        policy_limit = None
        policy_evidence = None

        if not matches:
            status = "missing_information"
            explanation = "No matching coverage limit was provided."

        elif len(matches) > 1:
            status = "needs_review"
            explanation = "Multiple matching limits require human review."

        else:
            match = matches[0]
            policy_limit = match.limit_amount
            policy_evidence = match.evidence

            if match.currency != requirement.currency:
                status = "needs_review"
                explanation = "Policy and requirement currencies differ."

            elif match.limit_amount < requirement.minimum_limit:
                status = "below_requirement"
                explanation = (
                    f"Reported limit {match.limit_amount} "
                    f"{match.currency} is below the required "
                    f"{requirement.minimum_limit} {requirement.currency}."
                )

            else:
                status = "limit_meets_minimum"
                explanation = (
                    "The numeric limit meets the stated minimum. "
                    "Other policy conditions require human review."
                )

        results.append(
            CoverageComparison(
                coverage_type=requirement.coverage_type,
                status=status,
                policy_limit=policy_limit,
                required_limit=requirement.minimum_limit,
                explanation=explanation,
                policy_evidence=policy_evidence,
                requirement_evidence=requirement.evidence,
            )
        )

    return results
