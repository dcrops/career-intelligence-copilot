"""Typed domain models for FR-005 Application Strategy.

These models consume trusted OpportunityAssessment and PortfolioMatch artifacts
and produce an evidence-backed application strategy. They intentionally omit
autonomous apply/skip decisions, CV/cover-letter content, outreach, submission,
and percentage scores.

Tier represents effort investment only. PursuitPosture is the primary
recommendation. The strategy recommends; it does not perform work.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import Identifier

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

ApplicationTier = Literal["platinum", "gold", "silver", "bronze"]

PursuitPosture = Literal[
    "prioritise",
    "pursue",
    "consider",
    "low_effort_submit",
    "do_not_prioritise",
    "insufficient_information",
]

PracticalValue = Literal[
    "career_priority",
    "acceptable_opportunity",
    "volume_obligation",
    "deferred_pending_information",
]

EffortLevel = Literal["full", "targeted", "minimal", "none"]

ReasonKind = Literal[
    "alignment",
    "constraint",
    "priority",
    "effort",
    "practical_value",
    "uncertainty",
]

Importance = Literal["material", "minor"]

EvidenceOrigin = Literal[
    "job_analysis",
    "career_profile",
    "opportunity_assessment",
    "portfolio_match",
]

AssessmentDimension = Literal["technical", "commercial", "portfolio"]

FitJudgment = Literal["strong", "moderate", "mixed", "weak", "misaligned", "unknown"]

NextActionKind = Literal[
    "consider_gathering_missing_job_information",
    "consider_reviewing_compensation",
    "consider_verifying_working_rights",
    "consider_reviewing_seniority_expectations",
    "consider_reviewing_location_or_arrangement",
    "consider_emphasising_portfolio_projects",
    "consider_cv_tailoring",
    "consider_cover_letter",
    "consider_low_effort_application",
    "consider_logging_and_deprioritising",
    "consider_owner_review",
]

JobEvidenceSource = Literal[
    "role_family",
    "seniority",
    "technology",
    "responsibility",
    "experience_requirement",
    "compensation",
    "location",
    "work_arrangement",
    "employment",
]

ProfileEvidenceSource = Literal[
    "skill",
    "experience",
    "project",
    "certification",
    "goal",
    "preference",
    "identity",
]

_LIST_JOB_SOURCES = frozenset(
    {
        "technology",
        "responsibility",
        "experience_requirement",
    }
)

_TIER_TO_EFFORT: dict[ApplicationTier, EffortLevel] = {
    "platinum": "full",
    "gold": "targeted",
    "silver": "minimal",
    "bronze": "none",
}

# Silver normally maps to minimal. Targeted silver is allowed only for credible
# seniority-stretch consider recommendations (strong technical/portfolio evidence
# without matching senior commercial AI employment).
_ALLOWED_EFFORT_FOR_TIER: dict[ApplicationTier, frozenset[EffortLevel]] = {
    "platinum": frozenset({"full"}),
    "gold": frozenset({"targeted"}),
    "silver": frozenset({"minimal", "targeted"}),
    "bronze": frozenset({"none"}),
}

_TAILORING_ACTION_KINDS = frozenset(
    {
        "consider_cv_tailoring",
        "consider_cover_letter",
    }
)

_TAILORING_TIERS = frozenset({"platinum", "gold"})


class StrategyModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobEvidenceRef(StrategyModel):
    """Pointer to an analysed job requirement with optional supporting excerpt."""

    source: JobEvidenceSource
    item_index: int | None = Field(default=None, ge=0)
    name: NonEmptyString | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def list_sources_require_item_index(self) -> JobEvidenceRef:
        if self.source in _LIST_JOB_SOURCES and self.item_index is None:
            raise ValueError(f"{self.source} job evidence requires item_index")
        return self


class ProfileEvidenceRef(StrategyModel):
    """Pointer to a career-profile entity. ``ref`` must resolve at service validation."""

    source: ProfileEvidenceSource
    ref: NonEmptyString
    excerpt: NonEmptyString | None = None


class StrategyEvidenceRef(StrategyModel):
    """Evidence citation tied to one trusted upstream origin."""

    origin: EvidenceOrigin
    job_evidence: JobEvidenceRef | None = None
    profile_evidence: ProfileEvidenceRef | None = None
    assessment_dimension: AssessmentDimension | None = None
    assessment_judgment: FitJudgment | None = None
    portfolio_project_id: Identifier | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def origin_fields_are_consistent(self) -> StrategyEvidenceRef:
        if self.origin == "job_analysis":
            if self.job_evidence is None:
                raise ValueError("job_analysis evidence requires job_evidence")
            if (
                self.profile_evidence is not None
                or self.assessment_dimension is not None
                or self.assessment_judgment is not None
                or self.portfolio_project_id is not None
            ):
                raise ValueError(
                    "job_analysis evidence may only include job_evidence "
                    "(and optional excerpt)"
                )
        elif self.origin == "career_profile":
            if self.profile_evidence is None:
                raise ValueError("career_profile evidence requires profile_evidence")
            if (
                self.job_evidence is not None
                or self.assessment_dimension is not None
                or self.assessment_judgment is not None
                or self.portfolio_project_id is not None
            ):
                raise ValueError(
                    "career_profile evidence may only include profile_evidence "
                    "(and optional excerpt)"
                )
        elif self.origin == "opportunity_assessment":
            if self.assessment_dimension is None:
                raise ValueError(
                    "opportunity_assessment evidence requires assessment_dimension"
                )
            if (
                self.job_evidence is not None
                or self.profile_evidence is not None
                or self.portfolio_project_id is not None
            ):
                raise ValueError(
                    "opportunity_assessment evidence may only include "
                    "assessment_dimension, optional assessment_judgment, "
                    "and optional excerpt"
                )
        elif self.origin == "portfolio_match":
            if self.portfolio_project_id is None:
                raise ValueError(
                    "portfolio_match evidence requires portfolio_project_id"
                )
            if (
                self.job_evidence is not None
                or self.profile_evidence is not None
                or self.assessment_dimension is not None
                or self.assessment_judgment is not None
            ):
                raise ValueError(
                    "portfolio_match evidence may only include "
                    "portfolio_project_id (and optional excerpt)"
                )
        return self


class StrategyReason(StrategyModel):
    """One explainable claim supporting the strategy recommendation."""

    kind: ReasonKind
    summary: NonEmptyString
    importance: Importance
    evidence: list[StrategyEvidenceRef] = Field(min_length=1)


class StrategyRiskOrGap(StrategyModel):
    """One risk or gap that may undermine the recommendation."""

    summary: NonEmptyString
    importance: Importance
    evidence: list[StrategyEvidenceRef] = Field(min_length=1)


class ManualCheck(StrategyModel):
    """Owner verification that could change the recommendation."""

    summary: NonEmptyString
    why_it_matters: NonEmptyString
    could_change_recommendation: bool
    evidence: list[StrategyEvidenceRef] = Field(min_length=1)


class NextAction(StrategyModel):
    """Advisory follow-up for the owner. Recommendations only — no execution."""

    kind: NextActionKind
    summary: NonEmptyString
    related_project_id: Identifier | None = None
    evidence: list[StrategyEvidenceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def related_project_id_matches_kind(self) -> NextAction:
        if self.kind == "consider_emphasising_portfolio_projects":
            return self
        if self.related_project_id is not None:
            raise ValueError(
                "related_project_id is only allowed when kind is "
                "'consider_emphasising_portfolio_projects'"
            )
        return self


class PortfolioEmphasis(StrategyModel):
    """Recommended portfolio project emphasis drawn from PortfolioMatch."""

    project_id: Identifier
    source_rank: int | None = Field(default=None, ge=1)
    summary: NonEmptyString
    evidence: list[StrategyEvidenceRef] = Field(min_length=1)


class ApplicationStrategy(StrategyModel):
    """Trusted application strategy for one opportunity.

    ``job_analysis`` is bound by ``ApplicationStrategyService`` from the
    caller-supplied OpportunityAssessment after posting-identity checks.
    OpportunityAssessment and PortfolioMatch are not embedded.
    """

    job_analysis: JobAnalysis
    application_tier: ApplicationTier
    pursuit_posture: PursuitPosture
    practical_value: PracticalValue
    effort_level: EffortLevel
    summary: NonEmptyString
    reasons: list[StrategyReason] = Field(min_length=1)
    risks_or_gaps: list[StrategyRiskOrGap] = Field(default_factory=list)
    manual_checks: list[ManualCheck] = Field(default_factory=list)
    next_actions: list[NextAction] = Field(default_factory=list, max_length=5)
    portfolio_emphasis: list[PortfolioEmphasis] = Field(default_factory=list)
    assumptions: list[NonEmptyString] = Field(default_factory=list)
    decision_blockers: list[NonEmptyString] = Field(default_factory=list)
    owner_review_required: Literal[True] = True
    insufficient_information: bool = False

    @model_validator(mode="after")
    def strategy_fields_are_consistent(self) -> ApplicationStrategy:
        allowed_effort = _ALLOWED_EFFORT_FOR_TIER[self.application_tier]
        if self.effort_level not in allowed_effort:
            expected = ", ".join(sorted(allowed_effort))
            raise ValueError(
                f"effort_level '{self.effort_level}' is inconsistent with "
                f"application_tier '{self.application_tier}' "
                f"(allowed: {expected})"
            )
        if (
            self.application_tier == "silver"
            and self.effort_level == "targeted"
            and self.pursuit_posture != "consider"
        ):
            raise ValueError(
                "effort_level 'targeted' with application_tier 'silver' requires "
                "pursuit_posture 'consider'"
            )

        if self.insufficient_information != (
            self.pursuit_posture == "insufficient_information"
        ):
            raise ValueError(
                "insufficient_information must be true if and only if "
                "pursuit_posture is 'insufficient_information'"
            )

        if self.practical_value == "volume_obligation" and self.pursuit_posture not in {
            "low_effort_submit",
            "consider",
        }:
            raise ValueError(
                "practical_value 'volume_obligation' requires pursuit_posture "
                "'low_effort_submit' or 'consider'"
            )

        for index, action in enumerate(self.next_actions):
            if action.kind in _TAILORING_ACTION_KINDS:
                if self.application_tier not in _TAILORING_TIERS:
                    raise ValueError(
                        f"next_actions[{index}].kind '{action.kind}' is only "
                        "allowed for platinum or gold application_tier"
                    )
            if action.kind == "consider_low_effort_application":
                if self.pursuit_posture != "low_effort_submit":
                    raise ValueError(
                        f"next_actions[{index}].kind "
                        "'consider_low_effort_application' requires "
                        "pursuit_posture 'low_effort_submit'"
                    )
            if action.kind == "consider_logging_and_deprioritising":
                if self.pursuit_posture != "do_not_prioritise" and (
                    self.application_tier != "bronze"
                ):
                    raise ValueError(
                        f"next_actions[{index}].kind "
                        "'consider_logging_and_deprioritising' requires "
                        "pursuit_posture 'do_not_prioritise' or "
                        "application_tier 'bronze'"
                    )

        return self
