"""FR-006c Summary Intelligence — evidence-backed Professional Summary composition.

Final polish targets Shield / Master recruiter impact: credibility-first personal
brand, role-specific later paragraphs, single-theme promotion, and scannable bold.

Pipeline (deterministic):

1. Gather supporting evidence from the Career Profile summary and Tailoring Plan
2. Determine dominant engineering themes
3. Determine strongest selling proposition
4. Determine job-specific emphasis
5. Compose a structured multi-paragraph summary
6. Apply grounded visual emphasis (first occurrence)
7. Validate grounding (no invented claims)
8. Return the final summary

Does not invent employers, technologies, metrics, industries, or achievements.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

# Recruiter-readable length; do not optimise for the fewest words.
_HARD_MAX_WORDS = 200

_FORBIDDEN_PHRASES = (
    "background:",
    "strengths in",
    "experience includes",
    "i possess",
    "i have experience",
)

_YEARS_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s+years?\s+of\s+commercial\s+enterprise\s+"
    r"Data Engineering\s+experience",
    re.IGNORECASE,
)

# Overall career positioning (default identity) — multi-domain, not domain-only.
_OVERALL_POSITIONING_RE = re.compile(
    r"(Experienced engineer with\s+\d+\+?\s*years?\s+across\s+"
    r"[^.]{10,200})",
    re.IGNORECASE,
)

_PORTFOLIO_ACROSS_RE = re.compile(
    r"(?:independent\s+)?AI Engineering portfolio work across\s+([^.;]+)",
    re.IGNORECASE,
)

_END_TO_END_RE = re.compile(
    r"end-to-end AI applications",
    re.IGNORECASE,
)

_PRODUCTION_MINDED_RE = re.compile(
    r"production-minded",
    re.IGNORECASE,
)

_METHODOLOGY_MARKERS = (
    "architecture-first",
    "evidence-based validation",
    "human-in-the-loop",
    "traceable, reviewable outputs",
    "applies a disciplined",
)

# Stable personal brand for paragraph 1 (candidate identity, not job title).
_BRAND_ROLE = "AI Engineer"

# Grounded scan phrases — bolded at most once when present.
_SCAN_PHRASES = (
    "production-minded AI applications",
    "end-to-end AI applications",
    "software engineering discipline",
    "AI engineering practices",
    "AI Engineering methodology",
    "architecture-first",
    "evidence-based validation",
    "human-in-the-loop",
    "explainable AI",
    "operational intelligence",
    "enterprise decision support",
    "retrieval systems",
    "retrieval-augmented generation",
)

# Portfolio domains used to broaden after a single job theme (evidence order).
_BROADEN_DOMAINS = (
    "retrieval systems",
    "retrieval-augmented generation",
    "explainable AI",
    "enterprise decision support",
    "operational intelligence",
)


@dataclass(frozen=True)
class SummaryEvidence:
    """Grounded facts available for composition."""

    brand_role: str
    source_summary: str
    tech_focus: tuple[str, ...]
    primary_theme: str | None
    overall_positioning: str | None
    commercial_years: str | None
    portfolio_domains: str | None
    portfolio_domain_parts: tuple[str, ...]
    builds_end_to_end: bool
    production_minded: bool
    methodology_sentence: str | None
    supporting_body: str | None


def compose_summary_intelligence(
    *,
    source_summary: str,
    target_role: str,
    themes: Sequence[str],
    promoted_skills: Sequence[str],
    methodology_philosophy: str | None = None,
) -> str:
    """Compose a recruiter-readable, evidence-backed Professional Summary.

    Returns ``source_summary`` unchanged when no plan emphasis exists.
    ``target_role`` is accepted for API compatibility; paragraph 1 uses the
    stable personal brand from the Career Profile summary.
    """
    del target_role  # Brand is stable; role-specific emphasis is plan-driven.
    body = " ".join(source_summary.split()).strip()
    if not body:
        return body

    evidence = gather_summary_evidence(
        source_summary=body,
        themes=themes,
        promoted_skills=promoted_skills,
        methodology_philosophy=methodology_philosophy,
    )
    if not evidence.tech_focus and not evidence.primary_theme:
        return _clamp_words(body, _HARD_MAX_WORDS)

    composed = compose_structured_summary(evidence)
    emphasised = apply_summary_bolding(
        composed,
        evidence,
        promoted_skills=promoted_skills,
    )
    validated = validate_summary_composition(
        emphasised,
        source_summary=body,
        allowed_labels=(
            *evidence.tech_focus,
            *((evidence.primary_theme,) if evidence.primary_theme else ()),
            evidence.brand_role,
        ),
    )
    return _clamp_words(validated, _HARD_MAX_WORDS)


def gather_summary_evidence(
    *,
    source_summary: str,
    themes: Sequence[str],
    promoted_skills: Sequence[str],
    methodology_philosophy: str | None = None,
    target_role: str | None = None,
) -> SummaryEvidence:
    """Collect and normalise evidence used by the composer."""
    del target_role
    brand_role = _brand_role_from_source(source_summary)
    theme_list = _dedupe_preserve(themes, limit=8)
    skill_list = _dedupe_preserve(promoted_skills, limit=8)
    skill_folded = {item.casefold() for item in skill_list}

    tech_focus = _select_tech_focus(theme_list, skill_list, brand_role)
    primary_theme = _select_primary_theme(
        theme_list,
        brand_role=brand_role,
        tech_focus=tech_focus,
        skill_folded=skill_folded,
    )

    years_match = _YEARS_RE.search(source_summary)
    commercial_years = years_match.group(1) if years_match else None

    overall_match = _OVERALL_POSITIONING_RE.search(source_summary)
    overall_positioning = (
        overall_match.group(1).strip().rstrip(".")
        if overall_match
        else None
    )

    portfolio_match = _PORTFOLIO_ACROSS_RE.search(source_summary)
    portfolio_domains = (
        portfolio_match.group(1).strip().rstrip(",")
        if portfolio_match
        else None
    )
    portfolio_domain_parts = tuple(
        part.strip()
        for part in re.split(r",| and ", portfolio_domains or "")
        if part.strip()
    )

    methodology_sentence = _extract_methodology_sentence(
        source_summary,
        methodology_philosophy=methodology_philosophy,
    )
    supporting_body = _supporting_body_without_role_prefix(
        source_summary, brand_role
    )

    return SummaryEvidence(
        brand_role=brand_role,
        source_summary=source_summary,
        tech_focus=tuple(tech_focus),
        primary_theme=primary_theme,
        overall_positioning=overall_positioning,
        commercial_years=commercial_years,
        portfolio_domains=portfolio_domains,
        portfolio_domain_parts=portfolio_domain_parts,
        builds_end_to_end=bool(_END_TO_END_RE.search(source_summary)),
        production_minded=bool(_PRODUCTION_MINDED_RE.search(source_summary)),
        methodology_sentence=methodology_sentence,
        supporting_body=supporting_body,
    )


def compose_structured_summary(evidence: SummaryEvidence) -> str:
    """Build a multi-paragraph who / what / how / value narrative."""
    paragraphs: list[str] = []

    who = _compose_who_paragraph(evidence)
    paragraphs.append(who)

    what = _compose_what_paragraph(evidence)
    if what and not _support_is_redundant(who, what):
        paragraphs.append(what)

    how = _compose_how_paragraph(evidence)
    if how and not any(_support_is_redundant(existing, how) for existing in paragraphs):
        paragraphs.append(how)

    forward = _compose_forward_paragraph(evidence)
    if forward and not any(
        _support_is_redundant(existing, forward) for existing in paragraphs
    ):
        paragraphs.append(forward)

    if len(paragraphs) == 1 and evidence.supporting_body:
        support = _strip_redundant_tech_clause(
            evidence.supporting_body, evidence.tech_focus
        )
        if support and not _support_is_redundant(who, support):
            paragraphs.append(support)

    return "\n\n".join(part.strip() for part in paragraphs if part and part.strip())


def apply_summary_bolding(
    summary: str,
    evidence: SummaryEvidence,
    *,
    promoted_skills: Sequence[str] = (),
) -> str:
    """Bold grounded scan phrases once each for ~10-second recruiter skimming.

    Brand paragraph only bolds credibility signals. Role tech and the primary
    theme are bolded in later paragraphs so openings stay visually consistent.
    """
    paragraphs = [part.strip() for part in summary.split("\n\n") if part.strip()]
    if not paragraphs:
        return summary

    source_folded = evidence.source_summary.casefold()
    plan_labels = {
        *(item.casefold() for item in evidence.tech_focus),
        *(
            {evidence.primary_theme.casefold()}
            if evidence.primary_theme
            else set()
        ),
        *(item.casefold() for item in promoted_skills),
    }

    def _grounded(phrases: Sequence[str], text: str) -> list[str]:
        out: list[str] = []
        for phrase in phrases:
            cleaned = phrase.strip()
            if len(cleaned) < 2 or cleaned.casefold() not in text.casefold():
                continue
            if _phrase_is_grounded(
                cleaned,
                source_folded=source_folded,
                plan_labels=plan_labels,
                evidence=evidence,
            ):
                out.append(cleaned)
        return out

    brand_phrases: list[str] = []
    if evidence.overall_positioning:
        brand_phrases.append(evidence.overall_positioning)
    elif evidence.commercial_years:
        # Supporting DE tenure only when overall positioning is absent.
        brand_phrases.append(
            f"{evidence.commercial_years} years of commercial enterprise "
            "Data Engineering"
        )
    brand_phrases.extend(
        [
            "production-minded AI applications",
            "end-to-end AI applications",
            "software engineering discipline",
        ]
    )
    brand = _bold_phrases(paragraphs[0], _grounded(brand_phrases, paragraphs[0]))
    if len(paragraphs) == 1:
        return brand

    rest_text = "\n\n".join(paragraphs[1:])
    rest_phrases: list[str] = []
    rest_phrases.extend(evidence.tech_focus)
    rest_phrases.extend(
        skill
        for skill in promoted_skills
        if skill.strip() and skill.casefold() in rest_text.casefold()
    )
    if evidence.primary_theme:
        rest_phrases.append(evidence.primary_theme)
    rest_phrases.extend(
        [
            "AI engineering practices",
            "AI Engineering methodology",
            "architecture-first",
            "evidence-based validation",
            "human-in-the-loop",
        ]
    )
    rest = _bold_phrases(rest_text, _grounded(rest_phrases, rest_text))
    return f"{brand}\n\n{rest}"


def _phrase_is_grounded(
    phrase: str,
    *,
    source_folded: str,
    plan_labels: set[str],
    evidence: SummaryEvidence,
) -> bool:
    folded = phrase.casefold()
    if folded in source_folded or folded in plan_labels:
        return True
    if folded == "production-minded ai applications":
        return evidence.production_minded
    if folded == "end-to-end ai applications":
        return evidence.builds_end_to_end
    if folded in {
        "software engineering discipline",
        "ai engineering practices",
        "ai engineering methodology",
    }:
        return evidence.methodology_sentence is not None or any(
            marker in source_folded for marker in _METHODOLOGY_MARKERS
        )
    if folded in {
        "architecture-first",
        "evidence-based validation",
        "human-in-the-loop",
        "explainable ai",
        "operational intelligence",
        "enterprise decision support",
        "retrieval systems",
        "retrieval-augmented generation",
    }:
        return folded in source_folded or folded in plan_labels
    return False


def validate_summary_composition(
    summary: str,
    *,
    source_summary: str,
    allowed_labels: Sequence[str],
) -> str:
    """Fail soft to source summary if composition violates grounding rules."""
    del allowed_labels
    plain = re.sub(r"\*\*", "", summary)
    text = " ".join(plain.split()).strip()
    if not text:
        return source_summary

    folded = text.casefold()
    if any(phrase in folded for phrase in _FORBIDDEN_PHRASES):
        return source_summary

    has_years = re.search(r"\b\d+(?:\.\d+)?\s+years?\b", text, re.IGNORECASE)
    source_has_years = re.search(
        r"\b\d+(?:\.\d+)?\s+years?\b", source_summary, re.IGNORECASE
    )
    if has_years and not source_has_years:
        return source_summary

    return summary.strip()


def _compose_who_paragraph(evidence: SummaryEvidence) -> str:
    """Paragraph 1 — stable personal brand: why interview this engineer."""
    if evidence.production_minded:
        product = "production-minded AI applications"
    elif evidence.builds_end_to_end:
        product = "end-to-end AI applications"
    else:
        product = "AI applications"

    # Prefer overall multi-domain positioning when present in the profile summary.
    if evidence.overall_positioning:
        lead = evidence.overall_positioning
        return (
            f"{lead}. Builds {product} with software engineering discipline."
        )

    role = evidence.brand_role

    # Domain-specific DE tenure is supporting evidence only — never the default
    # identity when overall positioning is absent.
    if evidence.commercial_years and evidence.portfolio_domains:
        credibility = (
            f"{role} with {evidence.commercial_years} years of commercial "
            "enterprise Data Engineering experience and an independent AI "
            "Engineering portfolio across "
            f"{evidence.portfolio_domains}."
        )
    elif evidence.commercial_years:
        credibility = (
            f"{role} with {evidence.commercial_years} years of commercial "
            "enterprise Data Engineering experience alongside independent AI "
            "Engineering portfolio delivery."
        )
    elif evidence.portfolio_domains:
        credibility = (
            f"{role} with an independent AI Engineering portfolio across "
            f"{evidence.portfolio_domains}."
        )
    elif "evidence-backed" in evidence.source_summary.casefold():
        return f"{role} designing and building evidence-backed systems."
    else:
        return f"{role} designing and building AI applications."

    return (
        f"{credibility} Builds {product} with software engineering discipline."
    )


def _compose_what_paragraph(evidence: SummaryEvidence) -> str | None:
    """Paragraph 2 — what they build; promote one job theme, then broaden."""
    tech = list(evidence.tech_focus[:3])
    if evidence.builds_end_to_end or evidence.production_minded:
        lead = "Designs and delivers these systems"
    else:
        lead = "Designs and builds AI applications"

    if tech:
        sentence = (
            f"{lead} with {_oxford_join(tech)}, applying modern "
            "AI engineering practices."
        )
    elif evidence.builds_end_to_end or evidence.production_minded:
        sentence = f"{lead}, applying modern AI engineering practices."
    else:
        return None

    theme = evidence.primary_theme
    # Portfolio span already appears in the stable brand paragraph — promote the
    # strongest job theme once here without restating the full domain list.
    if theme:
        sentence = f"{sentence.rstrip('.')} — with emphasis on {theme}."
    else:
        broaden = _broaden_domains(
            evidence.portfolio_domain_parts,
            exclude=None,
            limit=2,
        )
        if broaden:
            sentence = f"{sentence.rstrip('.')} across {_oxford_join(broaden)}."
    return sentence


def _compose_how_paragraph(evidence: SummaryEvidence) -> str | None:
    """Paragraph 3 — how they engineer."""
    if evidence.methodology_sentence:
        lowered = evidence.methodology_sentence.casefold()
        if (
            "architecture-first" in lowered
            or "human-in-the-loop" in lowered
            or "applies a disciplined" in lowered
            or "evidence-based validation" in lowered
        ):
            return (
                "Applies a disciplined AI Engineering methodology — "
                "architecture-first design, evidence-based validation, and "
                "human-in-the-loop review — to deliver AI systems with "
                "traceable, reviewable outputs."
            )
        sentence = evidence.methodology_sentence.strip()
        if not sentence.endswith("."):
            sentence += "."
        return sentence
    return None


def _compose_forward_paragraph(evidence: SummaryEvidence) -> str | None:
    """Paragraph 4 — value to deliver (no repeated methodology catchphrases)."""
    source = evidence.source_summary.casefold()
    can_close = (
        "operational decision-making" in source
        or "traceable, reviewable outputs" in source
        or evidence.methodology_sentence is not None
    )
    if not can_close:
        return None

    # Prefer advert-aligned close using remaining tech themes over repeating
    # "traceable, reviewable" already used in the methodology paragraph.
    tech = [item for item in evidence.tech_focus[:2] if item]
    if tech:
        return (
            f"Focused on delivering production AI systems with {_oxford_join(tech)} "
            "and clear engineering accountability for operational decision-making."
        )
    return (
        "Focused on delivering production AI systems with clear engineering "
        "accountability for operational decision-making."
    )


def _broaden_domains(
    domains: Sequence[str],
    *,
    exclude: str | None,
    limit: int,
) -> list[str]:
    """Pick adjacent portfolio domains, skipping the already-promoted theme."""
    exclude_key = exclude.casefold() if exclude else ""
    preferred_order = [item.casefold() for item in _BROADEN_DOMAINS]
    available = {
        part.casefold(): part
        for part in domains
        if part.strip() and part.casefold() != exclude_key
    }
    out: list[str] = []
    for key in preferred_order:
        if key in available:
            out.append(available[key])
            if len(out) >= limit:
                return out
    for part in domains:
        if part.casefold() == exclude_key:
            continue
        if part not in out:
            out.append(part)
        if len(out) >= limit:
            break
    return out


def _brand_role_from_source(source_summary: str) -> str:
    """Prefer the Career Profile brand opening when present."""
    body = source_summary.strip()
    if body.casefold().startswith(_BRAND_ROLE.casefold()):
        return _BRAND_ROLE
    return _BRAND_ROLE


def _select_tech_focus(
    themes: Sequence[str],
    skills: Sequence[str],
    brand_role: str,
) -> list[str]:
    """Prefer promoted skills that also appear as themes; fill from promoted."""
    role_key = brand_role.casefold()
    theme_folded = {item.casefold() for item in themes}
    ordered: list[str] = []
    seen: set[str] = set()

    def _take(skill: str) -> None:
        key = skill.casefold()
        if key == role_key or key in seen:
            return
        seen.add(key)
        ordered.append(skill)

    for skill in skills:
        if skill.casefold() in theme_folded or not theme_folded:
            _take(skill)
        if len(ordered) >= 3:
            return ordered
    for skill in skills:
        _take(skill)
        if len(ordered) >= 3:
            break
    return ordered


def _select_primary_theme(
    themes: Sequence[str],
    *,
    brand_role: str,
    tech_focus: Sequence[str],
    skill_folded: set[str],
) -> str | None:
    """Single strongest non-tech job theme for one-time promotion."""
    used = {brand_role.casefold(), *(item.casefold() for item in tech_focus)}
    for theme in themes:
        key = theme.casefold()
        if key in used:
            continue
        # Skip short skill-like labels already covered as technology.
        if key in skill_folded and " " not in theme and len(theme) < 18:
            continue
        return theme
    return None


def _extract_methodology_sentence(
    source_summary: str,
    *,
    methodology_philosophy: str | None,
) -> str | None:
    for sentence in _split_sentences(source_summary):
        folded = sentence.casefold()
        if any(marker in folded for marker in _METHODOLOGY_MARKERS):
            return sentence.strip()
    if methodology_philosophy:
        philosophy = " ".join(methodology_philosophy.split()).strip()
        if philosophy and any(
            marker in philosophy.casefold() for marker in _METHODOLOGY_MARKERS
        ):
            return philosophy
    return None


def _supporting_body_without_role_prefix(source_summary: str, role: str) -> str | None:
    body = source_summary.strip()
    overall = _OVERALL_POSITIONING_RE.search(body)
    if overall:
        remainder = body[overall.end() :].lstrip(" .")
        if remainder:
            remainder = remainder[0].upper() + remainder[1:]
            return remainder
        return None
    if body.casefold().startswith(role.casefold()):
        remainder = body[len(role) :].lstrip(" ,.-")
        if remainder.casefold().startswith("with "):
            remainder = remainder[5:]
        if remainder.casefold().startswith("applying "):
            remainder = remainder[9:]
        if remainder:
            remainder = remainder[0].upper() + remainder[1:]
            return remainder
        return None
    return body


def _support_is_redundant(opening: str, support: str) -> bool:
    """Skip supporting prose that restates earlier paragraphs without new facts."""
    opening_folded = re.sub(r"\*\*", "", opening).casefold()
    support_folded = re.sub(r"\*\*", "", support).casefold().strip().rstrip(".")
    if support_folded in opening_folded:
        return True
    support_tokens = [
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+\-/#]*", support_folded)
        if len(token) > 3
    ]
    if not support_tokens:
        return True
    overlap = sum(1 for token in support_tokens if token in opening_folded)
    return overlap >= max(2, len(support_tokens) - 1)


def _strip_redundant_tech_clause(text: str, tech_focus: Sequence[str]) -> str:
    if not tech_focus:
        return text
    cleaned = re.sub(
        r"\s+with\s+[A-Za-z0-9][A-Za-z0-9+.#/\-]*(?:\s*,\s*[A-Za-z0-9][A-Za-z0-9+.#/\-]*)*"
        r"(?:\s*,?\s+and\s+[A-Za-z0-9][A-Za-z0-9+.#/\-]*)?\s*\.?$",
        ".",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip()
    if cleaned.endswith(".."):
        cleaned = cleaned[:-1]
    if not cleaned.endswith("."):
        cleaned += "."
    return cleaned


def _bold_phrases(text: str, phrases: Sequence[str]) -> str:
    """Bold whole-phrase matches once each (longest first)."""
    if not text or not phrases:
        return text
    ordered = sorted(
        {phrase.strip() for phrase in phrases if phrase.strip()},
        key=len,
        reverse=True,
    )
    result = text
    for phrase in ordered:
        pattern = re.compile(
            rf"(?<!\*)\b({re.escape(phrase)})\b(?!\*)",
            re.IGNORECASE,
        )
        result = pattern.sub(r"**\1**", result, count=1)
    return result


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _dedupe_preserve(values: Sequence[str], *, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _oxford_join(items: Sequence[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _clamp_words(text: str, limit: int) -> str:
    """Clamp length while preserving paragraph breaks where possible."""
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        return text
    kept: list[str] = []
    word_count = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if word_count + len(words) <= limit:
            kept.append(paragraph)
            word_count += len(words)
            continue
        remaining = limit - word_count
        if remaining <= 12 or not kept:
            truncated = " ".join(words[:remaining]).rstrip(".,;:")
            for sep in (". ", "; "):
                idx = truncated.rfind(sep)
                if idx >= max(20, len(truncated) // 3):
                    truncated = truncated[: idx + 1].strip()
                    break
            else:
                truncated = truncated + "."
            kept.append(truncated)
        break
    return "\n\n".join(kept)
