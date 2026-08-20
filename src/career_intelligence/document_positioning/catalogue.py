"""Canonical capability identity catalogue.

M2: TailoringPlan's deterministic planner classifies through this module.
PositioningPlan and M4 letter selection use the same classifier. Master-adapt,
production cover-letter generation, and ``cic package prepare`` still must not
import it.

Design rules:
- Identities are canonical, not recruiter phrasing.
- Aliases collapse equivalent names onto one identity (RAG == Retrieval-Augmented Generation).
- RELATED pairs are explicit: a *requested* identity may be supported by a
  *different* profile identity. The requested identity remains unclaimable.
- Unknown labels are DIRECT on exact normalised match (PositioningPlan) or
  planner token-compatible match; they never invent RELATED.
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
        "microsoft_fabric",
        "data_pipeline",
        "llm",
        "openai",
        "langchain",
        "rest",
        "fastapi",
        "docker",
        "java",
        "javascript",
        "chatbot",
    }
)

# Normalised phrase -> identity. Justification lives in the M0/M2 reports.
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
    "microsoft fabric": "microsoft_fabric",
    "data pipeline": "data_pipeline",
    "data pipelines": "data_pipeline",
    "etl": "data_pipeline",
    "llm": "llm",
    "llms": "llm",
    "llm application development": "llm",
    "openai": "openai",
    "openai apis": "openai",
    "openai api": "openai",
    "azure openai": "openai",
    "gpt": "openai",
    "langchain": "langchain",
    "rest": "rest",
    "rest apis": "rest",
    "rest api": "rest",
    "api": "rest",
    "apis": "rest",
    "backend services": "rest",
    "backend service": "rest",
    "fastapi": "fastapi",
    "docker": "docker",
    "containers": "docker",
    "container": "docker",
    "containerisation": "docker",
    "containerization": "docker",
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
#
# M2 migrated justified live planner groups here. Deliberately omitted:
# RAG ↔ LLM (unsafe: retrieval systems are not generic LLM/platform claims)
# RAG ↔ chatbot, OpenAI ↔ chatbot, AWS ↔ Bedrock DIRECT.
_RELATED_PROFILE_IDENTITIES: dict[str, frozenset[str]] = {
    "aws_bedrock": frozenset({"aws"}),
    "azure": frozenset({"azure_data_factory", "microsoft_fabric"}),
    "azure_data_factory": frozenset({"azure", "microsoft_fabric", "data_pipeline"}),
    "microsoft_fabric": frozenset({"azure", "azure_data_factory"}),
    "data_pipeline": frozenset({"azure_data_factory"}),
    "llm": frozenset({"openai", "langchain"}),
    "openai": frozenset({"llm", "langchain"}),
    "langchain": frozenset({"llm", "openai"}),
    "rest": frozenset({"fastapi"}),
    "fastapi": frozenset({"rest"}),
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
                    f"Requested '{requested}' is not in the catalogue; it "
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


def aliases_for_identity(identity: str) -> tuple[str, ...]:
    """Return catalogue alias phrases that resolve to ``identity``, longest first."""
    aliases = [alias for alias, mapped in _ALIASES.items() if mapped == identity]
    aliases.sort(key=lambda item: (-len(item.split()), -len(item), item))
    return tuple(aliases)


def supporting_identities(identity: str) -> frozenset[str]:
    """Identities that may pack as evidence for ``identity``.

    Includes the identity itself plus explicit RELATED profile identities.
    Does not authorise claiming a different requested capability.
    """
    related = _RELATED_PROFILE_IDENTITIES.get(identity, frozenset())
    return frozenset({identity}) | related


def identities_mentioned_in_text(text: str) -> tuple[str, ...]:
    """Return catalogue identities whose aliases appear as token subsequences.

    Longer aliases win. A shorter alias is skipped when its tokens are a subset
    of an already-matched longer alias (so ``AWS Bedrock`` does not also emit
    a standalone ``aws`` identity from the same phrase).
    """
    tokens = _TOKEN_RE.findall(text.casefold())
    if not tokens:
        return ()
    ranked = sorted(
        _ALIASES.items(),
        key=lambda item: (-len(item[0].split()), -len(item[0]), item[0]),
    )
    found: list[str] = []
    matched_token_sets: list[frozenset[str]] = []
    for alias, identity in ranked:
        alias_tokens = alias.split()
        if not alias_tokens:
            continue
        if identity in found:
            continue
        if _has_contiguous_tokens(tokens, alias_tokens):
            alias_set = frozenset(alias_tokens)
            if any(alias_set <= prior for prior in matched_token_sets):
                continue
            found.append(identity)
            matched_token_sets.append(alias_set)
    return tuple(found)


def first_alias_in_text(text: str, identity: str) -> str | None:
    """Return the longest alias for ``identity`` that appears in ``text``."""
    tokens = _TOKEN_RE.findall(text.casefold())
    for alias in aliases_for_identity(identity):
        if _has_contiguous_tokens(tokens, alias.split()):
            return alias
    return None


def _has_contiguous_tokens(tokens: list[str], needle: list[str]) -> bool:
    if not needle or len(needle) > len(tokens):
        return False
    width = len(needle)
    for index in range(len(tokens) - width + 1):
        if tokens[index : index + width] == needle:
            return True
    return False


def _profile_identity_hits(profile_labels: Sequence[str]) -> dict[str, str]:
    """Map catalogue identity -> first profile label that resolved to it."""
    hits: dict[str, str] = {}
    for label in profile_labels:
        identity = resolve_identity(label)
        if identity is not None and identity not in hits:
            hits[identity] = label
    return hits
