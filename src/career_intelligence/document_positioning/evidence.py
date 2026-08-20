"""CareerProfile evidence collection for PositioningPlan.

JD technologies never enter this module as candidate labels.
"""

from __future__ import annotations

from career_intelligence.document_positioning.catalogue import (
    normalise_label,
    resolve_identity,
)
from career_intelligence.document_positioning.models import CandidateEvidenceRef
from career_intelligence.profile import CareerProfile, resolve_skill_evidence_refs
from career_intelligence.profile.models import Skill


def profile_capability_labels(profile: CareerProfile) -> tuple[str, ...]:
    """Candidate-owned names only: skills and demonstrated technologies."""
    labels: list[str] = []
    seen: set[str] = set()

    def _add(label: str) -> None:
        key = normalise_label(label)
        if not key or key in seen:
            return
        seen.add(key)
        labels.append(label)

    for skill in _iter_skills(profile):
        _add(skill.name)
    for project in profile.projects:
        for tech in project.technologies:
            _add(tech)
    for entry in profile.experience:
        for tech in entry.technologies:
            _add(tech)
    return tuple(labels)


def collect_evidence_refs(
    profile: CareerProfile,
    *,
    identity: str | None,
    label: str,
) -> tuple[CandidateEvidenceRef, ...]:
    """Return stable CareerProfile refs that support a promotable capability."""
    refs: list[CandidateEvidenceRef] = []
    seen: set[str] = set()

    def _push(source: str, ref: str) -> None:
        if ref in seen:
            return
        seen.add(ref)
        refs.append(CandidateEvidenceRef(source=source, ref=ref))  # type: ignore[arg-type]

    for skill in _iter_skills(profile):
        if not _label_supports(skill.name, identity=identity, fallback_label=label):
            continue
        _push("skill", f"skill:{skill.name}")
        for evidence in resolve_skill_evidence_refs(profile, skill):
            source = _source_from_ref(evidence.ref)
            if source is not None:
                _push(source, evidence.ref)

    for cert in sorted(profile.certifications, key=lambda item: item.id):
        if _cert_supports(cert.name, identity=identity, fallback_label=label):
            _push("certification", f"certification:{cert.id}")

    if identity is not None:
        extra_projects = 0
        for project in sorted(profile.projects, key=lambda item: item.id):
            if extra_projects >= 2:
                break
            if f"project:{project.id}" in seen:
                continue
            if any(
                _label_supports(tech, identity=identity, fallback_label=label)
                for tech in project.technologies
            ):
                _push("project", f"project:{project.id}")
                extra_projects += 1
        extra_experience = 0
        for entry in sorted(profile.experience, key=lambda item: item.id):
            if extra_experience >= 2:
                break
            if f"experience:{entry.id}" in seen:
                continue
            if any(
                _label_supports(tech, identity=identity, fallback_label=label)
                for tech in entry.technologies
            ):
                _push("experience", f"experience:{entry.id}")
                extra_experience += 1

    return tuple(refs)


def _iter_skills(profile: CareerProfile) -> list[Skill]:
    return [
        *profile.skills.technical,
        *profile.skills.domain,
        *profile.skills.soft,
    ]


def _label_supports(
    candidate_label: str,
    *,
    identity: str | None,
    fallback_label: str,
) -> bool:
    resolved = resolve_identity(candidate_label)
    if identity is not None:
        return resolved == identity
    return normalise_label(candidate_label) == normalise_label(fallback_label)


def _cert_supports(
    cert_name: str,
    *,
    identity: str | None,
    fallback_label: str,
) -> bool:
    if _label_supports(cert_name, identity=identity, fallback_label=fallback_label):
        return True
    if identity is None:
        return False
    resolved = resolve_identity(cert_name)
    if resolved is not None and resolved != identity:
        return False
    tokens = set(normalise_label(cert_name).split())
    identity_tokens = set(identity.split("_"))
    return bool(identity_tokens) and identity_tokens <= tokens


def _source_from_ref(ref: str) -> str | None:
    prefix, _, _rest = ref.partition(":")
    if prefix in {"skill", "experience", "project", "certification"}:
        return prefix
    return None
