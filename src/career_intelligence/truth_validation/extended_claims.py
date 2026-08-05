"""Deterministic detection for non-technology recruiter-document claims (FR-014 M4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence.truth_validation.catalogue import (
    AI_ENGINEERING_DURATION_KEY,
    COMMERCIAL_AI_KEY,
    COMMERCIAL_SOFTWARE_KEY,
    INDEPENDENT_ENGINEERING_KEY,
    SOFTWARE_ENGINEERING_DURATION_KEY,
)
from career_intelligence.truth_validation.models import (
    ArtefactKind,
    CandidateEvidenceCatalogue,
    Claim,
    ClaimClass,
    ClaimKind,
    ClaimStrength,
)
from career_intelligence.truth_validation.ids import new_claim_id
from career_intelligence.truth_validation.normalise import normalise_object_key

WELL_KNOWN_CERTIFICATIONS: tuple[str, ...] = (
    "AWS Certified Solutions Architect",
    "AWS Certified Developer",
    "AWS Certified Cloud Practitioner",
    "Microsoft Certified: Azure Fundamentals",
    "Microsoft Certified: Azure Developer Associate",
    "Google Cloud Professional Cloud Architect",
    "Certified Kubernetes Administrator",
    "PMP",
    "Scrum Master",
)
WELL_KNOWN_DOMAINS: tuple[str, ...] = (
    "financial services",
    "fintech",
    "healthcare",
    "government",
    "education",
    "retail",
    "telecommunications",
    "cybersecurity",
    "e-commerce",
)

_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_EMPLOYER = re.compile(
    r"\b(the role|this role|the position|your team|employer|company|job)\b.*\b"
    r"(requires|needs|uses|seeks|values|has)\b",
    re.I,
)
_ASPIRATION = re.compile(
    r"\b(interested in|keen to|hoping to|would like to|aspiring to|learn)\b", re.I
)
_DELIVERY = re.compile(
    r"\bI\s+(built|implemented|developed|deployed|delivered|created|shipped)\b",
    re.I,
)
_YEAR_NUMBER = (
    r"(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty)"
)
_YEARS = re.compile(
    rf"\b(?P<years>{_YEAR_NUMBER})\s*(?P<plus>\+|plus)?\s+years?\s+"
    r"(?:of\s+)?(?:experience\s+(?:with|in)\s+|of\s+)?(?P<object>[A-Za-z0-9+#.\-/ ]+?)"
    r"(?=(?:\s+(?:experience|development|engineering|work))?\s*(?:[,.!;]|$))",
    re.I,
)
_NUMBER_WORDS = {
    "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0,
    "six": 6.0, "seven": 7.0, "eight": 8.0, "nine": 9.0, "ten": 10.0,
    "eleven": 11.0, "twelve": 12.0, "thirteen": 13.0, "fourteen": 14.0,
    "fifteen": 15.0, "sixteen": 16.0, "seventeen": 17.0, "eighteen": 18.0,
    "nineteen": 19.0, "twenty": 20.0,
}
_EMPLOYMENT_LABELS = (
    ("commercial AI engineering", COMMERCIAL_AI_KEY),
    ("commercial AI experience", COMMERCIAL_AI_KEY),
    ("commercial software engineering", COMMERCIAL_SOFTWARE_KEY),
    ("commercial software experience", COMMERCIAL_SOFTWARE_KEY),
    ("independent engineering", INDEPENDENT_ENGINEERING_KEY),
    ("independent engineering experience", INDEPENDENT_ENGINEERING_KEY),
)


@dataclass(frozen=True)
class DetectedExtendedSpan:
    claim_kind: ClaimKind
    object_key: str
    surface_text: str
    sentence: str
    claim_class: ClaimClass
    strength: ClaimStrength
    detection_certainty: str
    start: int
    end: int
    claimed_years: float | None = None
    predicate: str = "has_evidence"
    years_precision: str | None = None


def detect_extended_spans(
    markdown: str,
    catalogue: CandidateEvidenceCatalogue,
) -> list[DetectedExtendedSpan]:
    """Detect employment, certifications, duration, delivery, and domain claims."""
    text = markdown or ""
    hits: list[DetectedExtendedSpan] = []
    for sentence, offset in _sentences(text):
        claim_class, certainty = _classify(sentence)
        hits.extend(_employment_hits(sentence, offset, claim_class, certainty))
        hits.extend(_label_hits(sentence, offset, claim_class, certainty, catalogue, "certification"))
        hits.extend(_label_hits(sentence, offset, claim_class, certainty, catalogue, "domain"))
        hits.extend(_duration_hits(sentence, offset, claim_class, certainty, catalogue))
        hits.extend(_delivery_hits(sentence, offset, claim_class, certainty, catalogue))
    hits.sort(key=lambda hit: (hit.start, hit.end, hit.claim_kind))
    return hits


def detect_extended_claims(
    markdown: str,
    catalogue: CandidateEvidenceCatalogue,
    *,
    artefact_kind: ArtefactKind,
) -> list[Claim]:
    """Return structured claims for deterministic extended detection hits."""
    return [
        Claim(
            claim_id=new_claim_id(),
            claim_class=hit.claim_class,
            claim_kind=hit.claim_kind,
            subject="candidate" if hit.claim_class in {"A", "C"} else "role",
            predicate=hit.predicate,
            object_key=hit.object_key,
            strength=hit.strength,
            surface_text=hit.surface_text,
            source_artefact=artefact_kind,
            span_hint=hit.sentence[:240],
        )
        for hit in detect_extended_spans(markdown, catalogue)
    ]


def _sentences(text: str) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    cursor = 0
    for part in _SENTENCE.split(text):
        start = text.find(part, cursor)
        cursor = start + len(part)
        if part.strip():
            result.append((part.strip(), start + (len(part) - len(part.lstrip()))))
    return result


def _classify(sentence: str) -> tuple[ClaimClass, str]:
    if _ASPIRATION.search(sentence):
        return "C", "certain"
    if _EMPLOYER.search(sentence):
        return "B", "certain"
    return "A", "certain"


def _employment_hits(sentence: str, offset: int, claim_class: ClaimClass, certainty: str) -> list[DetectedExtendedSpan]:
    hits = []
    for label, key in _EMPLOYMENT_LABELS:
        for match in re.finditer(rf"\b{re.escape(label)}\b", sentence, re.I):
            hits.append(_hit("employment", key, match.group(), sentence, claim_class, certainty,
                             offset + match.start(), offset + match.end(), "has_employment"))
    return hits


def _label_hits(sentence: str, offset: int, claim_class: ClaimClass, certainty: str,
                catalogue: CandidateEvidenceCatalogue, kind: ClaimKind) -> list[DetectedExtendedSpan]:
    labels: dict[str, str] = {}
    for entry in catalogue.entries:
        if kind in entry.claim_kinds:
            for label in [entry.display_label, entry.object_key, *entry.aliases]:
                if label:
                    labels[label] = entry.object_key
    for label in WELL_KNOWN_CERTIFICATIONS if kind == "certification" else WELL_KNOWN_DOMAINS:
        labels.setdefault(label, normalise_object_key(label))
    hits = []
    for label, key in sorted(labels.items(), key=lambda item: -len(item[0])):
        for match in re.finditer(rf"(?<!\w){re.escape(label)}(?!\w)", sentence, re.I):
            predicate = "holds_certification" if kind == "certification" else "has_domain_experience"
            hits.append(_hit(kind, key, match.group(), sentence, claim_class, certainty,
                             offset + match.start(), offset + match.end(), predicate))
    return hits


def _duration_hits(sentence: str, offset: int, claim_class: ClaimClass, certainty: str,
                   catalogue: CandidateEvidenceCatalogue) -> list[DetectedExtendedSpan]:
    hits = []
    for match in _YEARS.finditer(sentence):
        raw_object = match.group("object").strip()
        key = _resolve_duration_key(raw_object, catalogue)
        number = _NUMBER_WORDS.get(match.group("years").casefold())
        claimed = number if number is not None else float(match.group("years"))
        precision = "minimum" if match.group("plus") else "exact"
        ambiguous = key is None
        hits.append(_hit("duration", key or normalise_object_key(raw_object) or "unknown_duration",
                         match.group(), sentence, claim_class, "ambiguous" if ambiguous else certainty,
                         offset + match.start(), offset + match.end(), "has_duration",
                         claimed_years=claimed, years_precision="ambiguous" if ambiguous else precision))
    return hits


def _resolve_duration_key(label: str, catalogue: CandidateEvidenceCatalogue) -> str | None:
    candidate = normalise_object_key(label)
    for entry in catalogue.entries:
        if "technology" in entry.claim_kinds or "duration" in entry.claim_kinds:
            keys = {entry.object_key, *(normalise_object_key(alias) for alias in entry.aliases)}
            if candidate in keys:
                return entry.object_key
    aliases = {
        "software engineering": SOFTWARE_ENGINEERING_DURATION_KEY,
        "ai engineering": AI_ENGINEERING_DURATION_KEY,
        "artificial intelligence engineering": AI_ENGINEERING_DURATION_KEY,
    }
    return aliases.get(candidate)


def _delivery_hits(sentence: str, offset: int, claim_class: ClaimClass, certainty: str,
                   catalogue: CandidateEvidenceCatalogue) -> list[DetectedExtendedSpan]:
    match = _DELIVERY.search(sentence)
    if not match:
        return []
    projects = [entry for entry in catalogue.entries if "project_delivery" in entry.claim_kinds]
    for entry in projects:
        for label in [entry.display_label, entry.object_key, *entry.aliases]:
            if label:
                project_match = re.search(rf"(?<!\w){re.escape(label)}(?!\w)", sentence, re.I)
                if project_match:
                    return [_hit("project_delivery", entry.object_key, project_match.group(), sentence,
                                 claim_class, certainty, offset + match.start(),
                                 offset + project_match.end(), "delivered_project")]
    remainder = sentence[match.end():].strip(" .,:;")
    return [_hit("project_delivery", normalise_object_key(remainder) or "unknown_project",
                 sentence[match.start():], sentence, claim_class, "ambiguous",
                 offset + match.start(), offset + len(sentence), "delivered_project")]


def _hit(kind: ClaimKind, key: str, surface: str, sentence: str, claim_class: ClaimClass,
         certainty: str, start: int, end: int, predicate: str, *, claimed_years: float | None = None,
         years_precision: str | None = None) -> DetectedExtendedSpan:
    return DetectedExtendedSpan(kind, key, surface, sentence, claim_class, "experienced",
                                certainty, start, end, claimed_years, predicate, years_precision)
