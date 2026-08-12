"""Answer policy for AAS-0: authoritative data only; never guess."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnswerDecision(str, Enum):
    KNOWN = "known"
    PAUSE = "pause"


@dataclass(frozen=True)
class KnownAnswers:
    """Authoritative fill values derived from CIC / owner-approved seed."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    github_url: str | None = None
    # Explicit owner-approved extras collected during the live run (optional).
    extras: dict[str, str] = field(default_factory=dict)

    def as_lookup(self) -> dict[str, str]:
        """Flatten non-empty known values keyed by stable field ids."""
        base = {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "linkedin_url": self.linkedin_url,
            "portfolio_url": self.portfolio_url,
            "github_url": self.github_url,
        }
        out = {k: v for k, v in base.items() if isinstance(v, str) and v.strip()}
        for key, value in self.extras.items():
            if isinstance(value, str) and value.strip():
                out[key] = value.strip()
        return out


# Label fragments → known answer keys (deterministic; no inference of years/salary).
_LABEL_TO_KEY: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(full\s*name|your\s*name|candidate\s*name|legal\s*name)\b", re.I), "full_name"),
    (re.compile(r"\b(first\s*name|given\s*name)\b", re.I), "first_name"),
    (re.compile(r"\b(last\s*name|surname|family\s*name)\b", re.I), "last_name"),
    (re.compile(r"\be-?mail\b", re.I), "email"),
    (re.compile(r"\b(phone|mobile|contact\s*number|telephone)\b", re.I), "phone"),
    (re.compile(r"\b(city|suburb|location|where\s*do\s*you\s*live|address\s*line)\b", re.I), "location"),
    (re.compile(r"\blinkedin\b", re.I), "linkedin_url"),
    (re.compile(r"\b(portfolio|personal\s*website|website)\b", re.I), "portfolio_url"),
    (re.compile(r"\bgithub\b", re.I), "github_url"),
)

# Labels that must never be auto-answered without an explicit extras key.
_ALWAYS_PAUSE = re.compile(
    r"\b("
    r"salary|remuneration|package|notice\s*period|relocat|"
    r"clearance|citizenship|visa|work\s*rights|sponsor|"
    r"years?\s+of\s+experience|how\s+many\s+years|"
    r"why\s+(do\s+you\s+want|are\s+you\s+interested)|"
    r"cover\s*letter\s*text|additional\s*information|tell\s*us|"
    r"availability|start\s*date|hybrid|onsite|remote\s*work"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResolveResult:
    decision: AnswerDecision
    field_key: str | None = None
    value: str | None = None
    reason: str = ""


def _split_name(full_name: str | None) -> tuple[str | None, str | None]:
    if not full_name or not full_name.strip():
        return None, None
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def resolve_answer(label: str | None, known: KnownAnswers) -> ResolveResult:
    """Return KNOWN with value, or PAUSE. Never invent answers."""
    text = (label or "").strip()
    if not text:
        return ResolveResult(AnswerDecision.PAUSE, reason="empty_label")

    lookup = known.as_lookup()
    # Owner extras keyed by exact normalized question text.
    exact = re.sub(r"\s+", " ", text).strip().lower()
    extras_by_lower = {
        re.sub(r"\s+", " ", key).strip().lower(): (key, value)
        for key, value in known.extras.items()
    }
    if exact in extras_by_lower:
        key, value = extras_by_lower[exact]
        return ResolveResult(
            AnswerDecision.KNOWN,
            field_key=f"extra:{key}",
            value=value,
            reason="owner_approved_extra",
        )

    if _ALWAYS_PAUSE.search(text):
        # Only answer if an explicit extra matches the label key we would use.
        return ResolveResult(
            AnswerDecision.PAUSE,
            reason="ambiguous_or_sensitive_question",
        )

    first, last = _split_name(known.full_name)
    for pattern, key in _LABEL_TO_KEY:
        if not pattern.search(text):
            continue
        if key == "first_name":
            if first:
                return ResolveResult(
                    AnswerDecision.KNOWN, field_key=key, value=first, reason="profile_name"
                )
            return ResolveResult(AnswerDecision.PAUSE, field_key=key, reason="missing_first_name")
        if key == "last_name":
            if last:
                return ResolveResult(
                    AnswerDecision.KNOWN, field_key=key, value=last, reason="profile_name"
                )
            return ResolveResult(AnswerDecision.PAUSE, field_key=key, reason="missing_last_name")
        value = lookup.get(key)
        if value:
            return ResolveResult(
                AnswerDecision.KNOWN, field_key=key, value=value, reason="authoritative_cic"
            )
        return ResolveResult(AnswerDecision.PAUSE, field_key=key, reason="missing_known_value")

    return ResolveResult(AnswerDecision.PAUSE, reason="unrecognized_label")


def should_pause(label: str | None, known: KnownAnswers) -> bool:
    return resolve_answer(label, known).decision is AnswerDecision.PAUSE


def merge_owner_extra(known: KnownAnswers, question: str, answer: str) -> KnownAnswers:
    """Return a new KnownAnswers with an owner-approved extra for this run."""
    extras = dict(known.extras)
    extras[question.strip()] = answer.strip()
    return KnownAnswers(
        full_name=known.full_name,
        email=known.email,
        phone=known.phone,
        location=known.location,
        linkedin_url=known.linkedin_url,
        portfolio_url=known.portfolio_url,
        github_url=known.github_url,
        extras=extras,
    )


def known_answers_from_mapping(data: dict[str, Any]) -> KnownAnswers:
    """Build KnownAnswers from a plain mapping (tests / optional YAML)."""
    extras = data.get("extras") or {}
    if not isinstance(extras, dict):
        extras = {}
    return KnownAnswers(
        full_name=_opt_str(data.get("full_name")),
        email=_opt_str(data.get("email")),
        phone=_opt_str(data.get("phone")),
        location=_opt_str(data.get("location")),
        linkedin_url=_opt_str(data.get("linkedin_url")),
        portfolio_url=_opt_str(data.get("portfolio_url")),
        github_url=_opt_str(data.get("github_url")),
        extras={str(k): str(v) for k, v in extras.items()},
    )


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
