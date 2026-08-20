"""Capability identity catalogue v1 (M0).

Not wired into TailoringPlan, Master-adapt, cover-letter generation, or
``cic package prepare``. M1+ may consume this module. Production document
behaviour must remain unchanged until those milestones.

Design rules:
- Identities are canonical, not recruiter phrasing.
- Aliases collapse equivalent names onto one identity (RAG == Retrieval-Augmented Generation).
- RELATED pairs are explicit and one-directional in meaning: a requested identity
  may be supported by a *different* profile identity. The requested identity
  remains unclaimable.
- Unknown labels are DIRECT only on exact normalised identity match against
  profile labels; otherwise UNSUPPORTED. Unknown labels never invent RELATED.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from career_intelligence.document_positioning.models import (
    RequirementClassification,
    SupportStatus,
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Canonical identities justified by existing CIC tests / eval cases — not a
# general technology ontology.
_IDENTITIES: frozenset[str] = frozenset(
    {
        "rag",
        "aws",
        "aws_bedrock",
        "azure",
        "azure_data_factory",
        "java",
        "javascript",
        "chatbot",
    }
)

# Normalised phrase -> identity. Justification lives in the M0 audit report.
_ALIASES: dict[str, str] = {
    "rag": "rag",
    "retrieval augmented generation": "rag",
    "retrievalaugmented generation": "rag",
    "aws": "aws",
    "amazon web services": "aws",
    "aws bedrock": "aws_bedrock",
    "amazon bedrock": "aws_bedrock",
    "bedrock": "aws_bedrock",
    "azure": "azure",
    "microsoft azure": "azure",
    "azure data factory": "azure_data_factory",
    "data factory": "azure_data_factory",
    "adf": "azure_data_factory",
    "java": "java",
    "javascript": "javascript",
    "chatbot": "chatbot",
    "chatbots": "chatbot",
    "conversational ai": "chatbot",
    "conversational interfaces": "chatbot",
    "customer support agents": "chatbot",
    "virtual agents": "chatbot",
    "customer support automation": "chatbot",
}

# requested_identity -> frozenset of profile identities that may be promoted
# as RELATED evidence. Never treat the requested identity as claimed.
# v1 is not a drop-in for deterministic_planner._RELATED_CAPABILITY_GROUPS
# (for example Microsoft Fabric is not catalogued here).
_RELATED_PROFILE_IDENTITIES: dict[str, frozenset[str]] = {
    # Same cloud vendor; commercial AWS is transferable evidence for a Bedrock
    # role. Bedrock itself remains unclaimable without Bedrock evidence.
    "aws_bedrock": frozenset({"aws"}),
    # Existing FR-006 related-capability behaviour: JD Azure may promote ADF.
    "azure": frozenset({"azure_data_factory"}),
    "azure_data_factory": frozenset({"azure"}),
}


def normalise_label(label: str) -> str:
    """Lowercase alphanumeric tokens joined by spaces (hyphens become spaces)."""
    return " ".join(_TOKEN_RE.findall(label.casefold()))


def resolve_identity(label: str) -> str | None:
    """Return the catalogue identity for a label, or None if unknown."""
    normalised = normalise_label(label)
    if not normalised:
        return None
    identity = _ALIASES.get(normalised)
    if identity in _IDENTITIES:
        return identity
    if normalised in _IDENTITIES:
        return normalised
    return None


def classify_requirement(
    requested: str,
    profile_labels: Sequence[str],
) -> RequirementClassification:
    """Classify one employer-requested capability against profile evidence labels.

    Profile labels are treated as candidate-owned names (skills, project tech).
    The classifier never reads a job description as candidate evidence.
    """
    requested_identity = resolve_identity(requested)
    profile_hits = _profile_identity_hits(profile_labels)

    if requested_identity is not None and requested_identity in profile_hits:
        label = profile_hits[requested_identity]
        return RequirementClassification(
            requested_label=requested,
            requested_identity=requested_identity,
            status=SupportStatus.SUPPORTED_DIRECT,
            promotable_identity=requested_identity,
            promotable_profile_label=label,
            may_claim_requested=True,
            rationale=(
                f"Requested '{requested}' resolves to identity "
                f"'{requested_identity}', which is evidenced in the profile."
            ),
        )

    if requested_identity is not None:
        related_ids = _RELATED_PROFILE_IDENTITIES.get(requested_identity, frozenset())
        for related_id in sorted(related_ids):
            if related_id in profile_hits:
                return RequirementClassification(
                    requested_label=requested,
                    requested_identity=requested_identity,
                    status=SupportStatus.SUPPORTED_RELATED,
                    promotable_identity=related_id,
                    promotable_profile_label=profile_hits[related_id],
                    may_claim_requested=False,
                    rationale=(
                        f"Requested '{requested}' (identity '{requested_identity}') "
                        f"is not evidenced. Profile identity '{related_id}' is "
                        "explicit RELATED evidence and may be promoted. The "
                        "requested capability must not be claimed."
                    ),
                )
        return RequirementClassification(
            requested_label=requested,
            requested_identity=requested_identity,
            status=SupportStatus.UNSUPPORTED,
            promotable_identity=None,
            promotable_profile_label=None,
            may_claim_requested=False,
            rationale=(
                f"Requested '{requested}' (identity '{requested_identity}') has "
                "no direct or related profile evidence."
            ),
        )

    # Unknown requested phrasing: exact normalised match against a profile
    # label is DIRECT; otherwise UNSUPPORTED. No invented RELATED links.
    requested_norm = normalise_label(requested)
    for label in profile_labels:
        if normalise_label(label) == requested_norm and requested_norm:
            return RequirementClassification(
                requested_label=requested,
                requested_identity=None,
                status=SupportStatus.SUPPORTED_DIRECT,
                promotable_identity=None,
                promotable_profile_label=label,
                may_claim_requested=True,
                rationale=(
                    f"Requested '{requested}' is not in the v1 catalogue; it "
                    "matches a profile label exactly after normalisation."
                ),
            )
    return RequirementClassification(
        requested_label=requested,
        requested_identity=None,
        status=SupportStatus.UNSUPPORTED,
        promotable_identity=None,
        promotable_profile_label=None,
        may_claim_requested=False,
        rationale=(
            f"Requested '{requested}' is not a catalogue identity and does not "
            "exactly match a profile label."
        ),
    )


def _profile_identity_hits(profile_labels: Sequence[str]) -> dict[str, str]:
    """Map catalogue identity -> first profile label that resolved to it."""
    hits: dict[str, str] = {}
    for label in profile_labels:
        identity = resolve_identity(label)
        if identity is not None and identity not in hits:
            hits[identity] = label
    return hits
