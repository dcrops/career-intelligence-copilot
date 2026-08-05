"""Deterministic technology claim detection in Markdown (FR-014 M2).

Detects technology/framework mentions and classifies framing:
- Class A: candidate capability
- Class B: employer / role context
- Class C: aspiration / interest

Does not rewrite text. Does not use an LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from career_intelligence.truth_validation.aliases import (
    WELL_KNOWN_TECHNOLOGY_LABELS,
    alias_keys_for,
)
from career_intelligence.truth_validation.catalogue import catalogue_supports_technology
from career_intelligence.truth_validation.models import (
    ArtefactKind,
    CandidateEvidenceCatalogue,
    Claim,
    ClaimClass,
    ClaimStrength,
)
from career_intelligence.truth_validation.normalise import (
    display_label,
    normalise_object_key,
)
from career_intelligence.truth_validation.ids import new_claim_id

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Candidate-capability cues (Class A)
_CANDIDATE_CUES = re.compile(
    r"\b("
    r"i\s+(?:am|have|had|built|build|implemented|implement|developed|develop|"
    r"used|use|wrote|write|shipped|created|deliver|delivered|do|did)|"
    r"my\s+(?:best|strongest|experience|background|work|expertise|skills?)|"
    r"where\s+i\s+do\s+my\s+best|"
    r"i'?m\s+(?:proficient|experienced|expert|strongest)|"
    r"proficient\s+in|experienced\s+(?:in|with)|expert\s+(?:in|at)|"
    r"hands[- ]on\s+(?:with|experience)|"
    r"commercial\s+experience\s+with|"
    r"experience\s+with|experience\s+in"
    r")\b",
    re.IGNORECASE,
)

# Redwolf-style capability framing
_REDWOLF_FRAME = re.compile(
    r"roles?\s+centred\s+on\b.*\bwhere\s+i\s+do\s+my\s+best\b",
    re.IGNORECASE | re.DOTALL,
)

# Employer / role context (Class B)
_EMPLOYER_CUES = re.compile(
    r"\b("
    r"the\s+role\s+(?:uses|requires|needs|involves|centres\s+on|centers\s+on)|"
    r"this\s+role\s+(?:uses|requires|needs|involves)|"
    r"the\s+position\s+(?:uses|requires|needs)|"
    r"your\s+team\s+(?:uses|works\s+(?:in|with)|requires)|"
    r"you\s+(?:use|require|need)|"
    r"looking\s+for\s+(?:experience\s+)?(?:in|with)|"
    r"requires?\s+(?:experience\s+)?(?:in|with)|"
    r"must\s+have|nice\s+to\s+have|"
    r"the\s+stack\s+(?:includes|uses|is)|"
    r"tech\s+stack|"
    r"employer(?:'s)?\s+(?:stack|requirements?)|"
    r"job\s+(?:requires|uses|lists)"
    r")\b",
    re.IGNORECASE,
)

# Aspiration (Class C)
_ASPIRATION_CUES = re.compile(
    r"\b("
    r"interested\s+in\s+(?:expanding\s+into|learning|developing)|"
    r"keen\s+to\s+(?:learn|develop|expand)|"
    r"hoping\s+to\s+(?:learn|use|build)|"
    r"would\s+like\s+to\s+(?:learn|gain)|"
    r"aspiring\s+to|"
    r"expanding\s+into"
    r")\b",
    re.IGNORECASE,
)

_STRENGTH_PATTERNS: tuple[tuple[re.Pattern[str], ClaimStrength], ...] = (
    (re.compile(r"\b(expert|expertise)\b", re.I), "expert"),
    (re.compile(r"\b(strongest|best engineering)\b", re.I), "strongest"),
    (re.compile(r"\b(proficient|proficiency)\b", re.I), "proficient"),
    (re.compile(r"\b(experienced|experience with|experience in)\b", re.I), "experienced"),
    (re.compile(r"\b(interested|keen to learn|expanding into)\b", re.I), "interested"),
    (re.compile(r"\b(built|implemented|used|use|developed|shipped)\b", re.I), "used"),
)


@dataclass(frozen=True)
class DetectedTechnologySpan:
    """Internal detection hit before Claim construction."""

    label: str
    object_key: str
    surface_text: str
    sentence: str
    claim_class: ClaimClass
    strength: ClaimStrength
    detection_certainty: str  # certain | ambiguous
    start: int
    end: int


def build_technology_lexicon(
    catalogue: CandidateEvidenceCatalogue,
    *,
    extra_labels: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Return (display_label, object_key) pairs sorted longest-key-first."""
    labels: dict[str, str] = {}

    def _add(label: str) -> None:
        key = normalise_object_key(label)
        if len(key) < 2:
            return
        # Prefer longer / more specific display labels for the same key.
        current = labels.get(key)
        if current is None or len(label) > len(current):
            labels[key] = display_label(label)

    for entry in catalogue.entries:
        if "technology" not in entry.claim_kinds:
            continue
        if entry.display_label:
            _add(entry.display_label)
        _add(entry.object_key)
        for alias in entry.aliases:
            _add(alias)

    for label in WELL_KNOWN_TECHNOLOGY_LABELS:
        _add(label)
    for label in extra_labels or []:
        _add(label)

    items = [(display, key) for key, display in labels.items()]
    items.sort(key=lambda pair: (-len(pair[1]), -len(pair[0]), pair[0].casefold()))
    return items


def detect_technology_claims(
    markdown: str,
    catalogue: CandidateEvidenceCatalogue,
    *,
    artefact_kind: ArtefactKind,
    extra_labels: list[str] | None = None,
) -> list[Claim]:
    """Detect technology claims in Markdown and return structured Claim objects."""
    spans = detect_technology_spans(
        markdown,
        catalogue,
        extra_labels=extra_labels,
    )
    claims: list[Claim] = []
    for span in spans:
        claims.append(
            Claim(
                claim_id=new_claim_id(),
                claim_class=span.claim_class,
                claim_kind="technology",
                subject=(
                    "candidate"
                    if span.claim_class in {"A", "C"}
                    else "role"
                    if span.claim_class == "B"
                    else "candidate"
                ),
                predicate=(
                    "has_skill"
                    if span.claim_class == "A"
                    else "requires_skill"
                    if span.claim_class == "B"
                    else "interested_in_skill"
                ),
                object_key=span.object_key,
                strength=span.strength,
                surface_text=span.surface_text,
                source_artefact=artefact_kind,
                span_hint=span.sentence[:200],
            )
        )
    return claims


def detect_technology_spans(
    markdown: str,
    catalogue: CandidateEvidenceCatalogue,
    *,
    extra_labels: list[str] | None = None,
) -> list[DetectedTechnologySpan]:
    """Scan Markdown for technology spans and classify framing."""
    text = markdown or ""
    lexicon = build_technology_lexicon(catalogue, extra_labels=extra_labels)
    occupied: list[tuple[int, int]] = []
    hits: list[DetectedTechnologySpan] = []

    for display, key in lexicon:
        for match in _find_label_matches(text, display):
            start, end = match.span()
            if _overlaps(occupied, start, end):
                continue
            sentence = _sentence_at(text, start, end)
            classified = _classify_sentence(sentence)
            if classified is None:
                occupied.append((start, end))  # still occupy so shorter aliases skip
                continue
            claim_class, certainty = classified
            strength = _infer_strength(sentence, claim_class)
            occupied.append((start, end))
            hits.append(
                DetectedTechnologySpan(
                    label=display,
                    object_key=key,
                    surface_text=text[start:end],
                    sentence=sentence.strip(),
                    claim_class=claim_class,
                    strength=strength,
                    detection_certainty=certainty,
                    start=start,
                    end=end,
                )
            )

    hits.sort(key=lambda item: item.start)
    return hits


def _find_label_matches(text: str, label: str) -> list[re.Match[str]]:
    """Find case-insensitive whole-phrase matches for a technology label."""
    escaped = re.escape(label)
    # Allow flexible whitespace inside multi-word labels.
    escaped = escaped.replace(r"\ ", r"\s+")
    pattern = re.compile(rf"(?<![A-Za-z0-9_+#]){escaped}(?![A-Za-z0-9_+#])", re.I)
    return list(pattern.finditer(text))


def _overlaps(occupied: list[tuple[int, int]], start: int, end: int) -> bool:
    for left, right in occupied:
        if start < right and end > left:
            return True
    return False


def _sentence_at(text: str, start: int, end: int) -> str:
    left = 0
    right = len(text)
    for match in re.finditer(r"[.!?\n]", text):
        if match.end() <= start:
            left = match.end()
        elif match.start() >= end and right == len(text):
            right = match.end()
            break
    return text[left:right].strip()


def _classify_sentence(sentence: str) -> tuple[ClaimClass, str] | None:
    """Return (class, certainty) or None when the mention is not a material claim."""
    if _ASPIRATION_CUES.search(sentence):
        return "C", "certain"
    if _REDWOLF_FRAME.search(sentence):
        return "A", "certain"
    has_candidate = bool(_CANDIDATE_CUES.search(sentence))
    has_employer = bool(_EMPLOYER_CUES.search(sentence))
    if has_candidate and not has_employer:
        return "A", "certain"
    if has_employer and not has_candidate:
        return "B", "certain"
    if has_candidate and has_employer:
        return "A", "ambiguous"
    # Bare technology mention without framing cues is not treated as a claim
    # (false-positive safeguard). Lexicon occupancy still prevents double hits.
    return None


def _infer_strength(sentence: str, claim_class: ClaimClass) -> ClaimStrength:
    if claim_class == "C":
        return "interested"
    if claim_class == "B":
        return "mentioned"
    for pattern, strength in _STRENGTH_PATTERNS:
        if pattern.search(sentence):
            return strength
    if _REDWOLF_FRAME.search(sentence):
        return "strongest"
    return "experienced"


def technology_supported(
    catalogue: CandidateEvidenceCatalogue,
    object_key_or_label: str,
) -> bool:
    """True when catalogue has authoritative support for this technology."""
    if catalogue_supports_technology(catalogue, object_key_or_label) is not None:
        return True
    # Also try alias group keys against entry keys.
    for key in alias_keys_for(object_key_or_label):
        if catalogue_supports_technology(catalogue, key) is not None:
            return True
    return False
