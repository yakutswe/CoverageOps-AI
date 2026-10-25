
from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class CoverageType(str, Enum):
    GENERAL_LIABILITY = "general_liability"
    AUTO_LIABILITY = "auto_liability"
    PROPERTY = "property"
    WORKERS_COMPENSATION = "workers_compensation"
    UMBRELLA = "umbrella"


class PolicyEvidence(BaseModel):
    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1)


class CoverageLimit(BaseModel):
    coverage_type: CoverageType
    limit_amount: Decimal = Field(ge=0)
    currency: str = Field(default="USD")
    evidence: PolicyEvidence


class InsurancePolicy(BaseModel):
    policy_number: str = Field(min_length=1)
    insured_name: str = Field(min_length=1)
    carrier: str = Field(min_length=1)
    effective_date: date
    expiration_date: date
    limits: list[CoverageLimit] = Field(
        default_factory=list
    )
    exclusions: list[str] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if self.expiration_date <= self.effective_date:
            raise ValueError(
                "Policy expiration must be after effective date."
            )
        return self


class CoverageRequirement(BaseModel):
    coverage_type: CoverageType
    minimum_limit: Decimal = Field(ge=0)
    currency: str = "USD"
    evidence: PolicyEvidence


class CoverageComparison(BaseModel):
    coverage_type: CoverageType
    status: str
    policy_limit: Decimal | None
    required_limit: Decimal
    explanation: str
    policy_evidence: PolicyEvidence | None
    requirement_evidence: PolicyEvidence