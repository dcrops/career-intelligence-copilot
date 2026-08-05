"""Build CandidateEvidenceCatalogue from Career Profile (FR-014 M2/M4).

Only candidate-owned profile facts become ``candidate_authoritative`` entries.
JD / assessment / strategy / plans are never written into the catalogue here.

M4 adds employment honesty markers, certifications, domains, project delivery,
and deterministic tenure (supported_years) where dates allow.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from hashlib import sha256

from career_intelligence.profile.models import (
    CareerProfile,
    ExperienceEntry,
    Skill,
)
from career_intelligence.truth_validation.aliases import expand_alias_labels
from career_intelligence.truth_validation.ids import new_catalogue_entry_id
from career_intelligence.truth_validation.models import (
    CandidateEvidenceCatalogue,
    CatalogueEvidenceEntry,
    ClaimKind,
    EvidenceProvenance,
)
from career_intelligence.truth_validation.normalise import (
    display_label,
    normalise_object_key,
)

_AI_MARKERS = re.compile(
    r"\b("
    r"ai|artificial\s+intelligence|machine\s+learning|\bml\b|llm|gpt|"
    r"generative|rag|nlp|deep\s+learning|mlops|langgraph|langchain|"
    r"openai|anthropic|vector\s+search|embedding"
    r")\b",
    re.IGNORECASE,
)

_SOFTWARE_MARKERS = re.compile(
    r"\b("
    r"software|engineer|developer|data\s+engineer|platform|backend|"
    r"frontend|full[- ]?stack|devops|sre|architect"
    r")\b",
    re.IGNORECASE,
)

COMMERCIAL_AI_KEY = "commercial_ai_engineering"
COMMERCIAL_SOFTWARE_KEY = "commercial_software_engineering"
INDEPENDENT_ENGINEERING_KEY = "independent_engineering"
SOFTWARE_ENGINEERING_DURATION_KEY = "software_engineering"
AI_ENGINEERING_DURATION_KEY = "ai_engineering"


def build_catalogue_from_profile(
    profile: CareerProfile,
    *,
    built_at: datetime | None = None,
    catalogue_id: str | None = None,
    as_of: date | None = None,
) -> CandidateEvidenceCatalogue:
    """Populate a deterministic evidence catalogue from a Career Profile."""
    when = built_at or datetime.now(tz=UTC)
    as_of_date = as_of or when.date()
    entries: list[CatalogueEvidenceEntry] = []
    seen_keys: dict[str, CatalogueEvidenceEntry] = {}

    for skill in profile.skills.technical:
        _add_skill_entry(
            seen_keys,
            entries,
            skill,
            claim_kinds=("technology",),
            source_kind="profile_skill",
        )
    for skill in profile.skills.domain:
        _add_skill_entry(
            seen_keys,
            entries,
            skill,
            claim_kinds=("domain",),
            source_kind="profile_skill",
        )

    for experience in profile.experience:
        emp_kind = _employment_kind(experience)
        years = _experience_years(experience, as_of=as_of_date)
        years_known = years is not None

        for tech in experience.technologies:
            _add_labelled_entry(
                seen_keys,
                entries,
                label=tech,
                claim_kinds=("technology",),
                provenance=EvidenceProvenance(
                    source_kind="profile_experience",
                    authority="candidate_authoritative",
                    provenance_ref=f"experience:{experience.id}",
                    excerpt=tech,
                ),
                employment_kind=emp_kind,
                recency=_recency_for_experience(experience),
                supported_years=years if years_known else None,
                accumulate_years=years_known,
            )

        _add_employment_markers(
            seen_keys,
            entries,
            experience=experience,
            years=years,
            years_known=years_known,
        )

    for project in profile.projects:
        for tech in project.technologies:
            _add_labelled_entry(
                seen_keys,
                entries,
                label=tech,
                claim_kinds=("technology",),
                provenance=EvidenceProvenance(
                    source_kind="profile_project",
                    authority="candidate_authoritative",
                    provenance_ref=f"project:{project.id}",
                    excerpt=tech,
                ),
                employment_kind="portfolio",
                recency="current",
                supported_years=None,
                accumulate_years=False,
            )
        _add_labelled_entry(
            seen_keys,
            entries,
            label=project.name,
            claim_kinds=("project_delivery",),
            provenance=EvidenceProvenance(
                source_kind="profile_project",
                authority="candidate_authoritative",
                provenance_ref=f"project:{project.id}",
                excerpt=project.summary[:240],
            ),
            employment_kind="portfolio",
            recency="current",
            supported_years=None,
            accumulate_years=False,
            extra_aliases=[project.id.replace("-", " ")],
        )
        for demonstrates in project.demonstrates:
            _add_labelled_entry(
                seen_keys,
                entries,
                label=demonstrates,
                claim_kinds=("domain", "project_delivery"),
                provenance=EvidenceProvenance(
                    source_kind="profile_project",
                    authority="candidate_authoritative",
                    provenance_ref=f"project:{project.id}",
                    excerpt=demonstrates,
                ),
                employment_kind="portfolio",
                recency="current",
                supported_years=None,
                accumulate_years=False,
            )

    for cert in profile.certifications:
        _add_labelled_entry(
            seen_keys,
            entries,
            label=cert.name,
            claim_kinds=("certification",),
            provenance=EvidenceProvenance(
                source_kind="profile_certification",
                authority="candidate_authoritative",
                provenance_ref=f"certification:{cert.id}",
                excerpt=f"{cert.name} ({cert.status})",
            ),
            employment_kind=None,
            recency="current" if cert.status == "active" else "historical",
            supported_years=None,
            accumulate_years=False,
            extra_aliases=[cert.issuer, cert.id.replace("-", " ")],
        )

    fingerprint = _profile_fingerprint(profile)
    return CandidateEvidenceCatalogue(
        catalogue_id=catalogue_id or f"cat_{fingerprint[:16]}",
        built_at=when,
        profile_fingerprint=fingerprint,
        entries=entries,
    )


def catalogue_supports_technology(
    catalogue: CandidateEvidenceCatalogue,
    label: str,
) -> CatalogueEvidenceEntry | None:
    """Return a candidate_authoritative technology entry matching ``label``, if any."""
    return catalogue_supports_kind(catalogue, label, kinds=("technology", "domain"))


def catalogue_supports_kind(
    catalogue: CandidateEvidenceCatalogue,
    label: str,
    *,
    kinds: tuple[ClaimKind, ...],
) -> CatalogueEvidenceEntry | None:
    """Return an authoritative catalogue entry matching label for any of ``kinds``."""
    keys = {normalise_object_key(label)}
    from career_intelligence.truth_validation.aliases import alias_keys_for

    keys |= set(alias_keys_for(label))
    for entry in catalogue.entries:
        if entry.provenance.authority != "candidate_authoritative":
            continue
        if not any(kind in entry.claim_kinds for kind in kinds):
            continue
        entry_keys = {entry.object_key} | {
            normalise_object_key(alias) for alias in entry.aliases
        }
        if keys & entry_keys:
            return entry
    return None


def catalogue_entry_by_key(
    catalogue: CandidateEvidenceCatalogue,
    object_key: str,
    *,
    kinds: tuple[ClaimKind, ...] | None = None,
) -> CatalogueEvidenceEntry | None:
    key = normalise_object_key(object_key)
    for entry in catalogue.entries:
        if entry.provenance.authority != "candidate_authoritative":
            continue
        if kinds is not None and not any(k in entry.claim_kinds for k in kinds):
            continue
        if entry.object_key == key:
            return entry
        if any(normalise_object_key(alias) == key for alias in entry.aliases):
            return entry
    return None


def _add_employment_markers(
    seen_keys: dict[str, CatalogueEvidenceEntry],
    entries: list[CatalogueEvidenceEntry],
    *,
    experience: ExperienceEntry,
    years: float | None,
    years_known: bool,
) -> None:
    text_blob = " ".join(
        [
            experience.title,
            experience.organisation,
            *experience.highlights,
            *experience.technologies,
        ]
    )
    is_ai = bool(_AI_MARKERS.search(text_blob))
    is_software = bool(_SOFTWARE_MARKERS.search(text_blob)) or is_ai

    if experience.kind == "independent_engineering":
        _add_labelled_entry(
            seen_keys,
            entries,
            label="independent engineering",
            claim_kinds=("employment",),
            provenance=EvidenceProvenance(
                source_kind="profile_experience",
                authority="candidate_authoritative",
                provenance_ref=f"experience:{experience.id}",
                excerpt=experience.title,
            ),
            employment_kind="independent",
            recency=_recency_for_experience(experience),
            supported_years=years if years_known else None,
            accumulate_years=years_known,
            forced_key=INDEPENDENT_ENGINEERING_KEY,
            extra_aliases=["independent engineering experience", "independent work"],
        )
        if is_ai:
            _add_labelled_entry(
                seen_keys,
                entries,
                label="AI engineering",
                claim_kinds=("duration", "domain"),
                provenance=EvidenceProvenance(
                    source_kind="profile_experience",
                    authority="candidate_authoritative",
                    provenance_ref=f"experience:{experience.id}",
                    excerpt=experience.title,
                ),
                employment_kind="independent",
                recency=_recency_for_experience(experience),
                supported_years=years if years_known else None,
                accumulate_years=years_known,
                forced_key=AI_ENGINEERING_DURATION_KEY,
            )
        return

    if experience.kind != "employment":
        return

    if is_software:
        _add_labelled_entry(
            seen_keys,
            entries,
            label="commercial software engineering",
            claim_kinds=("employment", "duration"),
            provenance=EvidenceProvenance(
                source_kind="profile_experience",
                authority="candidate_authoritative",
                provenance_ref=f"experience:{experience.id}",
                excerpt=experience.title,
            ),
            employment_kind="commercial",
            recency=_recency_for_experience(experience),
            supported_years=years if years_known else None,
            accumulate_years=years_known,
            forced_key=COMMERCIAL_SOFTWARE_KEY,
            extra_aliases=[
                "commercial software experience",
                "commercial software engineering experience",
                "software engineering",
            ],
        )
        _add_labelled_entry(
            seen_keys,
            entries,
            label="software engineering",
            claim_kinds=("duration",),
            provenance=EvidenceProvenance(
                source_kind="profile_experience",
                authority="candidate_authoritative",
                provenance_ref=f"experience:{experience.id}",
                excerpt=experience.title,
            ),
            employment_kind="commercial",
            recency=_recency_for_experience(experience),
            supported_years=years if years_known else None,
            accumulate_years=years_known,
            forced_key=SOFTWARE_ENGINEERING_DURATION_KEY,
        )

    if is_ai:
        _add_labelled_entry(
            seen_keys,
            entries,
            label="commercial AI engineering",
            claim_kinds=("employment", "duration"),
            provenance=EvidenceProvenance(
                source_kind="profile_experience",
                authority="candidate_authoritative",
                provenance_ref=f"experience:{experience.id}",
                excerpt=experience.title,
            ),
            employment_kind="commercial",
            recency=_recency_for_experience(experience),
            supported_years=years if years_known else None,
            accumulate_years=years_known,
            forced_key=COMMERCIAL_AI_KEY,
            extra_aliases=[
                "commercial AI experience",
                "commercial AI engineering experience",
                "commercial artificial intelligence",
            ],
        )
        _add_labelled_entry(
            seen_keys,
            entries,
            label="AI engineering",
            claim_kinds=("duration", "domain"),
            provenance=EvidenceProvenance(
                source_kind="profile_experience",
                authority="candidate_authoritative",
                provenance_ref=f"experience:{experience.id}",
                excerpt=experience.title,
            ),
            employment_kind="commercial",
            recency=_recency_for_experience(experience),
            supported_years=years if years_known else None,
            accumulate_years=years_known,
            forced_key=AI_ENGINEERING_DURATION_KEY,
        )


def _add_skill_entry(
    seen_keys: dict[str, CatalogueEvidenceEntry],
    entries: list[CatalogueEvidenceEntry],
    skill: Skill,
    *,
    claim_kinds: tuple[ClaimKind, ...],
    source_kind: str,
) -> None:
    _add_labelled_entry(
        seen_keys,
        entries,
        label=skill.name,
        claim_kinds=claim_kinds,
        provenance=EvidenceProvenance(
            source_kind=source_kind,  # type: ignore[arg-type]
            authority="candidate_authoritative",
            provenance_ref=f"skill:{skill.name}",
            excerpt=skill.name,
        ),
        employment_kind=None,
        recency="current",
        supported_years=None,
        accumulate_years=False,
    )


def _add_labelled_entry(
    seen_keys: dict[str, CatalogueEvidenceEntry],
    entries: list[CatalogueEvidenceEntry],
    *,
    label: str,
    claim_kinds: tuple[ClaimKind, ...],
    provenance: EvidenceProvenance,
    employment_kind: str | None,
    recency: str | None,
    supported_years: float | None,
    accumulate_years: bool,
    forced_key: str | None = None,
    extra_aliases: list[str] | None = None,
) -> None:
    key = forced_key or normalise_object_key(label)
    if not key:
        return
    aliases = [
        display_label(item)
        for item in expand_alias_labels(label)
        if normalise_object_key(item) != key
    ]
    for alias in extra_aliases or []:
        if alias and normalise_object_key(alias) != key:
            aliases.append(display_label(alias))

    if key in seen_keys:
        existing = seen_keys[key]
        merged_kinds = list(dict.fromkeys([*existing.claim_kinds, *claim_kinds]))
        merged_aliases = list(dict.fromkeys([*existing.aliases, *aliases]))
        keep_prov = existing.provenance
        if (
            existing.provenance.source_kind != "profile_skill"
            and provenance.source_kind == "profile_skill"
        ):
            keep_prov = provenance
        merged_years = existing.supported_years
        if accumulate_years and supported_years is not None:
            merged_years = (merged_years or 0.0) + supported_years
        elif supported_years is not None and merged_years is None:
            merged_years = supported_years
        updated = existing.model_copy(
            update={
                "claim_kinds": merged_kinds,
                "aliases": merged_aliases,
                "provenance": keep_prov,
                "employment_kind": existing.employment_kind or employment_kind,
                "recency": existing.recency or recency,
                "supported_years": merged_years,
            }
        )
        idx = entries.index(existing)
        entries[idx] = updated
        seen_keys[key] = updated
        return

    entry = CatalogueEvidenceEntry(
        entry_id=new_catalogue_entry_id(),
        object_key=key,
        display_label=display_label(label),
        aliases=aliases,
        claim_kinds=list(claim_kinds),
        employment_kind=employment_kind,  # type: ignore[arg-type]
        recency=recency,  # type: ignore[arg-type]
        supported_years=supported_years,
        provenance=provenance,
    )
    entries.append(entry)
    seen_keys[key] = entry


def _employment_kind(experience: ExperienceEntry) -> str:
    if experience.kind == "employment":
        return "commercial"
    if experience.kind == "independent_engineering":
        return "independent"
    return "other"


def _recency_for_experience(experience: ExperienceEntry) -> str:
    if experience.end_date is None:
        return "current"
    return "historical"


def _experience_years(experience: ExperienceEntry, *, as_of: date) -> float | None:
    """Return tenure in years, or None when dates are insufficient."""
    start = experience.start_date
    end = experience.end_date or as_of
    if end < start:
        return None
    days = (end - start).days
    if days < 0:
        return None
    return round(days / 365.25, 2)


def _profile_fingerprint(profile: CareerProfile) -> str:
    payload = profile.model_dump_json().encode("utf-8")
    return sha256(payload).hexdigest()
