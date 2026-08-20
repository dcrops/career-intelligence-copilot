"""M0 design types for capability classification.

PositioningPlan is intentionally not implemented in this milestone.
These types freeze DIRECT / RELATED / UNSUPPORTED semantics for the v1 catalogue.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
