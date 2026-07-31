"""Typed contracts for Application Preparation Orchestration (FR-011 M0).

A preparation run coordinates existing services for an Opportunity whose owner
decision is already ``apply``. Upstream FR-002–FR-005 artefacts are preconditions
— they are verified, not re-produced. Package business rules stay in
``ApplicationPackageService``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from career_intelligence.opportunities.models import OpportunityId

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PreparationRunId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^apr_[0-9A-HJKMNP-TV-Z]{26}$"),
]

PreparationStatus = Literal["running", "completed", "failed"]
PreparationStepId = Literal["validate_preconditions", "prepare_package"]

PREPARATION_STEPS: tuple[PreparationStepId, ...] = (
    "validate_preconditions",
    "prepare_package",
)


class PreparationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CompletedStepRecord(PreparationModel):
    step_id: PreparationStepId
    completed_at: datetime


class PreparationErrorInfo(PreparationModel):
    step_id: PreparationStepId | None = None
    message: NonEmptyString
    error_type: NonEmptyString | None = None


class PackageResultRef(PreparationModel):
    """Reference to the package produced by ``ApplicationPackageService``."""

    opportunity_id: OpportunityId
    prepared_at: datetime


class PreparationRunState(PreparationModel):
    """Durable audit record for one preparation orchestration run.

    Not the Opportunity system of record and not a package manifest. Stores
    coordination evidence only.
    """

    run_id: PreparationRunId
    opportunity_id: OpportunityId
    status: PreparationStatus
    created_at: datetime
    updated_at: datetime
    completed_steps: list[CompletedStepRecord] = Field(default_factory=list)
    package: PackageResultRef | None = None
    error: PreparationErrorInfo | None = None
