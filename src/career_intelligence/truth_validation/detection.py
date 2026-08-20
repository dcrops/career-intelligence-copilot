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
from career_intelligence.truth_validation.canonical_identity import (
    canonical_identity,
    scan_labels_for_identity,
)
from career_intelligence.truth_validation.catalogue import catalogue_supports_technology
from career_intelligence.truth_validation.ids import new_claim_id
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

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")

# Candidate-capability cues (Class A)
_CANDIDATE_CUES = re.compile(
    r"\b("
    r"i\s+(?:am|have|had|built|build|implemented|implement|developed|develop|"
    r"used|use|wrote|write|shipped|created|deliver|delivered|did)|"
    r"i\s+do(?!\s+not)|"
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

# Explicit denial of THIS span. Matched in the local clause before the span.
# Do not treat a sentence-level "not" as global negation.
_DENIAL_BEFORE_SPAN = re.compile(
    r"\b("
    r"do\s+not\s+claim|don't\s+claim|"
    r"do\s+not\s+have|don't\s+have|"
    r"have\s+not\s+(?:used|worked|claimed)|haven't\s+(?:used|worked|claimed)|"
    r"has\s+not\s+(?:used|worked)|"
    r"have\s+not\s+used|did\s+not\s+use|didn't\s+use|"
    r"never\s+(?:used|claimed|worked\s+with)|"
    r"no\s+direct\s+experience\s+with|"
    r"without\s+(?:direct\s+)?experience\s+with"
    r")\b",
    re.IGNORECASE,
)

_CLAUSE_BREAK = re.compile(
    r",\s*(?:but|however|although|though|yet|and\s+I\b|I\b)\b|;\s+|\.\s+",
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
        if not ({"technology", "domain"} & set(entry.claim_kinds)):
            continue
        if entry.display_label:
            _add(entry.display_label)
        _add(entry.object_key)
        for alias in entry.aliases:
            _add(alias)
        for source in (entry.display_label, entry.object_key, *entry.aliases):
            if not source:
                continue
            for phrase in scan_labels_for_identity(source):
                _add(phrase)

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
            if _span_is_denied(sentence, text, start):
                occupied.append((start, end))
                continue
            classified = _classify_sentence(sentence)
            if classified is None:
                occupied.append((start, end))  # still occupy so shorter aliases skip
                continue
            claim_class, certainty = classified
            strength = _infer_strength(sentence, claim_class)
            identity = canonical_identity(display) or canonical_identity(text[start:end])
            object_key = normalise_object_key(identity) if identity else key
            occupied.append((start, end))
            hits.append(
                DetectedTechnologySpan(
                    label=display,
                    object_key=object_key,
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


def _span_is_denied(sentence: str, text: str, span_start: int) -> bool:
    """True when this span is under an explicit local denial, not a later claim."""
    folded_sentence = sentence
    rel = _relative_span_start(sentence, text, span_start)
    if rel < 0:
        rel = 0
    clause_start = 0
    for break_match in _CLAUSE_BREAK.finditer(folded_sentence):
        if break_match.end() <= rel:
            clause_start = break_match.end()
        elif break_match.start() >= rel:
            break
    prefix = folded_sentence[clause_start:rel]
    return bool(_DENIAL_BEFORE_SPAN.search(prefix))


def _relative_span_start(sentence: str, text: str, span_start: int) -> int:
    """Locate ``sentence`` in ``text`` nearest ``span_start`` and return offset in sentence."""
    search_from = 0
    best = -1
    while True:
        found = text.find(sentence, search_from)
        if found < 0:
            break
        if found <= span_start < found + len(sentence):
            return span_start - found
        if best < 0 or abs(found - span_start) < abs(best - span_start):
            best = found
        search_from = found + 1
    if best < 0:
        return 0
    return max(0, span_start - best)


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
