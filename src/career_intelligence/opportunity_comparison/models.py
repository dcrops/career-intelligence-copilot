"""Typed models for ranked comparison of open opportunities (M4)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from career_intelligence.application_strategy.models import ApplicationTier, PursuitPosture
from career_intelligence.opportunities.models import PipelineStatus

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ComparisonModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RankedOpportunity(ComparisonModel):
    """One open opportunity in a prioritised ordering with explainable reasons."""

    rank: int = Field(ge=1)
    opportunity_id: NonEmptyString
    company: NonEmptyString | None = None
    title: NonEmptyString | None = None
    status: PipelineStatus
    pursuit_posture: PursuitPosture | None = None
    application_tier: ApplicationTier | None = None
    fit_strength: int = Field(ge=0)
    technical_fit: NonEmptyString | None = None
    commercial_fit: NonEmptyString | None = None
    portfolio_fit: NonEmptyString | None = None
    reasons: list[NonEmptyString] = Field(min_length=1)


class OpportunityComparison(ComparisonModel):
    """Deterministic ranking of open opportunities for owner effort prioritisation."""

    generated_at: datetime
    open_only: bool = True
    open_count: int = Field(ge=0)
    excluded_count: int = Field(ge=0)
    items: list[RankedOpportunity]
    owner_review_required: bool = True
