"""PositioningPlan contract (M1) and M0 classification types.

``PositioningPlan`` is a deterministic semantic contract. It does not contain
CV or cover-letter prose. It must not be imported by ``cic package prepare``
until a later milestone.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

NeedKind = Literal["technology", "responsibility", "experience_requirement"]
RequirementLevel = Literal["required", "preferred", "unspecified"]
TrajectoryMode = Literal["full_chapters", "bridge", "ai_lead"]
ForbiddenReason = Literal["related_unclaimable", "unsupported"]
SpineKind = Literal["direct", "related", "gap", "trajectory", "portfolio"]
EvidenceSource = Literal["skill", "experience", "project", "certification"]

CV_REWRITE_SURFACE: tuple[str, ...] = (
    "professional_summary",
    "selected_engineering_highlights",
    "optional_project_relevance_line",
    "skills_emphasis",
)

LOCKED_MASTER_SECTIONS: tuple[str, ...] = (
    "experience_headings_dates_relationship",
    "experience_bullets",
    "project_bodies",
    "courses",
    "certifications",
    "contact",
)


class SupportStatus(str, Enum):
    """How a requested employer capability relates to candidate evidence."""

    SUPPORTED_DIRECT = "supported_direct"
    SUPPORTED_RELATED = "supported_related"
    UNSUPPORTED = "unsupported"


class PositioningModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class RequirementClassification(PositioningModel):
    """Result of classifying one employer-requested capability against profile labels.

    ``SUPPORTED_RELATED`` promotes the candidate's real related capability. It
    never authorises claiming the employer's requested capability itself.
    """

    requested_label: str
    requested_identity: str | None = None
    status: SupportStatus
    promotable_identity: str | None = None
    promotable_profile_label: str | None = None
    may_claim_requested: bool
    rationale: str = Field(min_length=1)


class EmployerNeed(PositioningModel):
    """One ordered hiring requirement. Employer context, never candidate evidence."""

    rank: int = Field(ge=1)
    kind: NeedKind
    label: str
    level: RequirementLevel | None = None
    item_index: int = Field(ge=0)
    excerpt: str | None = None


class CandidateEvidenceRef(PositioningModel):
    """Pointer to CareerProfile evidence. Not JD text."""

    source: EvidenceSource
    ref: NonEmptyString


class ClassifiedNeed(PositioningModel):
    need: EmployerNeed
    classification: RequirementClassification
    evidence_refs: tuple[CandidateEvidenceRef, ...] = ()


class ArgumentClaim(PositioningModel):
    """Packed truthful statement for later bounded generation. Not recruiter prose."""

    kind: SpineKind
    statement: NonEmptyString
    evidence_refs: tuple[CandidateEvidenceRef, ...] = ()
    need_rank: int | None = None


class ForbiddenClaim(PositioningModel):
    """Semantic prohibition: do not express this as candidate capability."""

    requested_label: NonEmptyString
    may_not_claim: NonEmptyString
    reason: ForbiddenReason
    identity: str | None = None


class PositioningPlan(PositioningModel):
    """Deterministic employer-facing positioning strategy for one job."""

    employer_needs: tuple[ClassifiedNeed, ...]
    argument_spine: tuple[ArgumentClaim, ...]
    forbidden_claims: tuple[ForbiddenClaim, ...]
    selected_evidence_refs: tuple[CandidateEvidenceRef, ...]
    include_methodology: bool
    include_methodology_rationale: NonEmptyString
    trajectory_mode: TrajectoryMode
    trajectory_rationale: NonEmptyString
    cv_rewrite_surface: tuple[str, ...] = CV_REWRITE_SURFACE
    locked_master_sections: tuple[str, ...] = LOCKED_MASTER_SECTIONS
