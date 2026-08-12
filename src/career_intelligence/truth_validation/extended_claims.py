"""Deterministic detection for non-technology recruiter-document claims (FR-014 M4)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence.truth_validation.catalogue import (
    AI_ENGINEERING_DURATION_KEY,
    COMMERCIAL_AI_KEY,
    COMMERCIAL_SOFTWARE_KEY,
    DATA_ENGINEERING_DURATION_KEY,
    INDEPENDENT_ENGINEERING_KEY,
    OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY,
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
_YEARS_ACROSS = re.compile(
    rf"\b(?P<years>{_YEAR_NUMBER})\s*(?P<plus>\+|plus)?\s+years?\s+across\s+"
    r"(?P<object>[^.!?;]+)",
    re.I,
)
_YEARS_AS_ROLE = re.compile(
    rf"\b(?P<years>{_YEAR_NUMBER})\s*(?P<plus>\+|plus)?\s+years?\s+as\s+"
    r"(?:an?\s+)?(?P<object>[A-Za-z0-9+#.\-/ ]+?)\s*(?=[,.!;]|$)",
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
    """Detect certification/domain labels, preferring longer spans over nested truncations.

    Well-known short labels (e.g. ``AWS Certified Developer``) can be substrings of a more
    specific certification expression (e.g. ``AWS Certified Developer - Associate``). Without
    occupancy, both fire and the truncated twin can falsely block when the longer claim is
    authoritatively supported. Matches technology/duration overlap policy: longest-first,
    skip spans that overlap an already accepted hit.
    """
    labels: dict[str, str] = {}
    for entry in catalogue.entries:
        if kind in entry.claim_kinds:
            for label in [entry.display_label, entry.object_key, *entry.aliases]:
                if label:
                    labels[label] = entry.object_key
    for label in WELL_KNOWN_CERTIFICATIONS if kind == "certification" else WELL_KNOWN_DOMAINS:
        labels.setdefault(label, normalise_object_key(label))
    hits: list[DetectedExtendedSpan] = []
    occupied: list[tuple[int, int]] = []
    predicate = "holds_certification" if kind == "certification" else "has_domain_experience"
    for label, key in sorted(labels.items(), key=lambda item: (-len(item[0]), item[0].casefold())):
        for match in re.finditer(rf"(?<!\w){re.escape(label)}(?!\w)", sentence, re.I):
            start = offset + match.start()
            end = offset + match.end()
            if _spans_overlap(occupied, start, end):
                continue
            occupied.append((start, end))
            hits.append(
                _hit(
                    kind,
                    key,
                    match.group(),
                    sentence,
                    claim_class,
                    certainty,
                    start,
                    end,
                    predicate,
                )
            )
    return hits


def _spans_overlap(occupied: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(start < right and end > left for left, right in occupied)


def _duration_hits(sentence: str, offset: int, claim_class: ClaimClass, certainty: str,
                catalogue: CandidateEvidenceCatalogue) -> list[DetectedExtendedSpan]:
    hits = []
    for pattern in (_YEARS_ACROSS, _YEARS_AS_ROLE, _YEARS):
        for match in pattern.finditer(sentence):
            raw_object = match.group("object").strip()
            if pattern is _YEARS:
                raw_object = _extend_duration_object(raw_object, sentence[match.end() :])
            key = _resolve_duration_key(raw_object, catalogue, pattern=pattern)
            number = _NUMBER_WORDS.get(match.group("years").casefold())
            claimed = number if number is not None else float(match.group("years"))
            precision = "minimum" if match.group("plus") else "exact"
            ambiguous = key is None
            hits.append(_hit(
                "duration",
                key or normalise_object_key(raw_object) or "unknown_duration",
                match.group(),
                sentence,
                claim_class,
                "ambiguous" if ambiguous else certainty,
                offset + match.start(),
                offset + match.end(),
                "has_duration",
                claimed_years=claimed,
                years_precision="ambiguous" if ambiguous else precision,
            ))
    # Prefer longer / more specific matches when overlapping.
    hits.sort(key=lambda hit: (hit.start, -(hit.end - hit.start), hit.end))
    deduped: list[DetectedExtendedSpan] = []
    covered: list[tuple[int, int]] = []
    for hit in hits:
        if any(hit.start < end and hit.end > start for start, end in covered):
            continue
        deduped.append(hit)
        covered.append((hit.start, hit.end))
    return deduped


def _extend_duration_object(raw_object: str, remainder: str) -> str:
    """Attach trailing domain nouns the non-greedy years regex left behind."""
    trailing = re.match(
        r"\s+(engineering|development|experience)\b",
        remainder,
        re.I,
    )
    if not trailing:
        return raw_object
    folded = raw_object.casefold()
    noun = trailing.group(1)
    if noun.casefold() in folded:
        return raw_object
    return f"{raw_object} {noun}".strip()


def _resolve_duration_key(
    label: str,
    catalogue: CandidateEvidenceCatalogue,
    *,
    pattern: re.Pattern[str] | None = None,
) -> str | None:
    folded = label.casefold().strip()
    folded = re.sub(r"\s+experience$", "", folded).strip()
    candidate = normalise_object_key(folded)

    # Multi-domain "across …" → overall engineering floor only.
    if pattern is _YEARS_ACROSS or _is_overall_multi_domain_object(folded):
        return OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY

    # "years as an AI Engineer" / similar role titles → domain AI duration.
    if pattern is _YEARS_AS_ROLE:
        if "ai engineer" in folded or folded in {"ai", "artificial intelligence"}:
            return AI_ENGINEERING_DURATION_KEY
        if "data engineer" in folded:
            return DATA_ENGINEERING_DURATION_KEY

    # Dual-domain inflation without overall "across" framing.
    if _is_data_and_ai_inflation(folded):
        return AI_ENGINEERING_DURATION_KEY

    for entry in catalogue.entries:
        if "technology" in entry.claim_kinds or "duration" in entry.claim_kinds:
            keys = {entry.object_key, *(normalise_object_key(alias) for alias in entry.aliases)}
            if candidate in keys:
                return entry.object_key
    aliases = {
        normalise_object_key("software engineering"): SOFTWARE_ENGINEERING_DURATION_KEY,
        normalise_object_key("ai engineering"): AI_ENGINEERING_DURATION_KEY,
        normalise_object_key("applied ai engineering"): AI_ENGINEERING_DURATION_KEY,
        normalise_object_key("artificial intelligence engineering"): AI_ENGINEERING_DURATION_KEY,
        normalise_object_key("data engineering"): DATA_ENGINEERING_DURATION_KEY,
        normalise_object_key("commercial ai engineering"): COMMERCIAL_AI_KEY,
        normalise_object_key("commercial artificial intelligence engineering"): COMMERCIAL_AI_KEY,
        normalise_object_key("commercial software engineering"): COMMERCIAL_SOFTWARE_KEY,
        normalise_object_key("overall engineering experience"): (
            OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY
        ),
        normalise_object_key("overall engineering"): (
            OVERALL_ENGINEERING_EXPERIENCE_DURATION_KEY
        ),
    }
    return aliases.get(candidate)


def _is_overall_multi_domain_object(folded: str) -> bool:
    if "across" not in folded:
        return False
    markers = (
        "testing",
        "automation",
        "data engineering",
        "ai engineering",
        "applied ai",
    )
    return sum(1 for marker in markers if marker in folded) >= 2


def _is_data_and_ai_inflation(folded: str) -> bool:
    if "across" in folded:
        return False
    has_data = "data" in folded and "engineering" in folded
    has_ai = "ai" in folded or "artificial intelligence" in folded
    return has_data and has_ai


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
