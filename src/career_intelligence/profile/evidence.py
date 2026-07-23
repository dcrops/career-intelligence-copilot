"""Capability evidence strength derived from the Career Profile.

Skills remain truthful capability claims. Evidence strength records *how* a
capability is demonstrated so downstream planners can prioritise without inventing
or deleting facts.

Legacy ``Skill.evidence`` strings (``experience:id; project:id``) are resolved
against the profile. Optional structured ``Skill.evidence_refs`` take precedence
when present.

Strength ordering (strongest first) is intentional and explainable — not a
scoring engine. Callers compare kinds via ``evidence_strength_rank``.
"""

from __future__ import annotations

from typing import Literal

from career_intelligence.profile.models import CareerProfile, Skill, SkillEvidenceRef

SkillEvidenceKind = Literal[
    "employment",
    "independent_engineering",
    "portfolio_project",
    "certification",
    "professional_development",
    "coursework",
    "unspecified",
]

# Lower rank = stronger demonstration for prioritisation.
_EVIDENCE_STRENGTH_RANK: dict[SkillEvidenceKind, int] = {
    "employment": 0,
    "independent_engineering": 1,
    "portfolio_project": 2,
    "certification": 3,
    "professional_development": 4,
    "coursework": 5,
    "unspecified": 6,
}

_EXPERIENCE_KIND_TO_EVIDENCE: dict[str, SkillEvidenceKind] = {
    "employment": "employment",
    "independent_engineering": "independent_engineering",
    "professional_development": "professional_development",
}


def evidence_strength_rank(kind: SkillEvidenceKind) -> int:
    """Return sort key for evidence strength (lower is stronger)."""
    return _EVIDENCE_STRENGTH_RANK[kind]


def parse_legacy_evidence_tokens(evidence: str | None) -> list[tuple[str, str]]:
    """Parse ``namespace:id`` tokens from a legacy semicolon-separated evidence string."""
    if not evidence:
        return []
    tokens: list[tuple[str, str]] = []
    for part in evidence.split(";"):
        piece = part.strip()
        if not piece or ":" not in piece:
            continue
        namespace, _, identifier = piece.partition(":")
        namespace = namespace.strip().casefold()
        identifier = identifier.strip()
        if namespace and identifier:
            tokens.append((namespace, identifier))
    return tokens


def resolve_skill_evidence_refs(
    profile: CareerProfile,
    skill: Skill,
) -> list[SkillEvidenceRef]:
    """Return structured evidence refs for a skill (explicit or legacy-derived)."""
    if skill.evidence_refs:
        return list(skill.evidence_refs)

    experience_by_id = {entry.id: entry for entry in profile.experience}
    project_ids = {project.id for project in profile.projects}
    certification_ids = {cert.id for cert in profile.certifications}

    resolved: list[SkillEvidenceRef] = []
    seen: set[tuple[str, str]] = set()
    for namespace, identifier in parse_legacy_evidence_tokens(skill.evidence):
        kind: SkillEvidenceKind | None = None
        ref = f"{namespace}:{identifier}"
        if namespace == "experience":
            entry = experience_by_id.get(identifier)
            if entry is not None:
                kind = _EXPERIENCE_KIND_TO_EVIDENCE[entry.kind]
        elif namespace == "project":
            if identifier in project_ids:
                kind = "portfolio_project"
        elif namespace in {"certification", "cert"}:
            if identifier in certification_ids:
                kind = "certification"
                ref = f"certification:{identifier}"
        if kind is None:
            continue
        key = (kind, ref)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(SkillEvidenceRef(kind=kind, ref=ref))
    return resolved


def strongest_evidence_kind(
    profile: CareerProfile,
    skill: Skill,
) -> SkillEvidenceKind:
    """Strongest evidence kind backing a skill (or ``unspecified``)."""
    refs = resolve_skill_evidence_refs(profile, skill)
    if not refs:
        return "unspecified"
    return min((ref.kind for ref in refs), key=evidence_strength_rank)


def strongest_evidence_kind_for_capability(
    profile: CareerProfile,
    capability_name: str,
) -> SkillEvidenceKind:
    """Best evidence kind for a named capability (skill match, else project tech)."""
    best: SkillEvidenceKind = "unspecified"
    best_rank = evidence_strength_rank(best)
    for skill in (
        *profile.skills.technical,
        *profile.skills.domain,
        *profile.skills.soft,
    ):
        if skill.name.casefold() != capability_name.casefold():
            continue
        kind = strongest_evidence_kind(profile, skill)
        rank = evidence_strength_rank(kind)
        if rank < best_rank:
            best = kind
            best_rank = rank

    # Portfolio technologies without a skill row still count as portfolio evidence.
    for project in profile.projects:
        for tech in project.technologies:
            if tech.casefold() != capability_name.casefold():
                continue
            rank = evidence_strength_rank("portfolio_project")
            if rank < best_rank:
                best = "portfolio_project"
                best_rank = rank
    return best
