"""Deterministic application-strategy planner for FR-005.

Package-private production recommendation path. Returns an untrusted payload;
callers must obtain trusted output through ApplicationStrategyService.

The planner is rule-based and explainable. It does not use LLMs, embeddings,
percentage scores, or autonomous apply/skip decisions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import (
    FitDimensionAssessment,
    FitFinding,
    OpportunityAssessment,
)
from career_intelligence.portfolio_matching.models import PortfolioMatch
from career_intelligence.profile.models import CareerProfile, Preferences

from .context import SearchOperatingContext
from .models import ApplicationTier, EffortLevel, PracticalValue, PursuitPosture
from .planner import ApplicationStrategyPayload

_TIER_TO_EFFORT: dict[ApplicationTier, EffortLevel] = {
    "platinum": "full",
    "gold": "targeted",
    "silver": "minimal",
    "bronze": "none",
}

_JUDGMENT_RANK: dict[str, int] = {
    "strong": 5,
    "moderate": 4,
    "mixed": 3,
    "weak": 2,
    "misaligned": 1,
    "unknown": 0,
}

_AI_TARGET_FAMILIES = frozenset(
    {
        "ai_engineering",
        "ai_solutions",
        "ml_engineering",
    }
)

_AI_ADJACENT_FAMILIES = frozenset(
    {
        "software_engineering",
        "ai_adjacent",
    }
)

_STRETCH_SENIORITY = frozenset({"lead", "principal", "manager"})
_SENIOR_OR_ABOVE = _STRETCH_SENIORITY | frozenset({"senior"})

# Tokens that mark an employment entry as AI-related (title / technologies / highlights).
_AI_ROLE_TOKENS = (
    "ai engineer",
    "ai engineering",
    "artificial intelligence",
    "machine learning",
    "ml engineer",
    "ml engineering",
    "llm",
    "generative ai",
    "genai",
    "deep learning",
)

# Tokens that mark senior commercial ownership within AI employment.
_SENIOR_OWNERSHIP_TOKENS = (
    "senior",
    "lead",
    "principal",
    "staff",
    "manager",
    "head of",
    "ownership",
    "owned",
    "production",
    "deployed",
    "deployment",
    "governance",
    "lifecycle",
    "executive",
    "c-suite",
    "c suite",
    "ceo",
    "cto",
    "leadership",
    "led ",
    "leading",
    "team lead",
)

# Finding-text tokens for material senior commercial / leadership gaps.
_SENIOR_COMMERCIAL_GAP_TOKENS = (
    "senior",
    "executive",
    "c-suite",
    "c suite",
    "ceo",
    "cto",
    "leadership",
    "commercial ownership",
    "commercial ai",
    "production leadership",
    "production ai",
    "ownership",
    "partner",
    "partnership",
    "c-level",
    "c level",
)

# JobAnalysis text tokens for senior commercial / executive leadership expectations.
# Intentionally excludes bare "senior" so title-only Senior roles do not auto-cap.
_JOB_SENIOR_LEADERSHIP_TOKENS = (
    "executive",
    "c-suite",
    "c suite",
    "ceo",
    "cto",
    "c-level",
    "c level",
    "leadership",
    "commercial ownership",
    "production leadership",
    "partnering with",
    "partnership with",
    "working one-on-one with the ceo",
    "working one-on-one with the cto",
    "working directly with the ceo",
    "working directly with the cto",
    "report to the ceo",
    "report to the cto",
    "reporting to the ceo",
    "reporting to the cto",
)

_WORKING_RIGHTS_TOKENS = (
    "working rights",
    "work rights",
    "unrestricted australian",
    "right to work",
    "visa",
)

_MAX_PORTFOLIO_EMPHASIS = 3
_MAX_NEXT_ACTIONS = 5

_PARENTHETICAL_RE = re.compile(r"\([^)]*\)")
_LEADING_ARRANGEMENT_RE = re.compile(
    r"^(?:hybrid|remote|onsite|on[\s-]?site)\s+",
    re.IGNORECASE,
)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_WHITESPACE_RE = re.compile(r"\s+")

# Longest-first phrase replacements for Australian state/territory aliases.
_STATE_PHRASE_ALIASES: tuple[tuple[str, str], ...] = (
    ("australian capital territory", "act"),
    ("new south wales", "nsw"),
    ("northern territory", "nt"),
    ("south australia", "sa"),
    ("western australia", "wa"),
    ("victoria", "vic"),
    ("queensland", "qld"),
    ("tasmania", "tas"),
)

_ROLE_FAMILY_LABELS: dict[str, str] = {
    "ai_engineering": "AI engineering",
    "ai_solutions": "AI solutions",
    "ml_engineering": "ML engineering",
    "software_engineering": "software engineering",
    "data_engineering": "data engineering",
    "network_engineering": "network engineering",
    "data_science": "data science",
    "ai_adjacent": "AI-adjacent",
    "other": "other",
    "unknown": "unknown",
}


@dataclass
class _Signals:
    technical: FitDimensionAssessment
    commercial: FitDimensionAssessment
    portfolio: FitDimensionAssessment
    role_family: str
    ai_aligned: bool
    outside_ai_priority: bool
    employment_blocker: str | None = None
    salary_conflict: bool = False
    salary_unknown: bool = False
    salary_min_unset: bool = False
    location_mismatch: bool = False
    arrangement_mismatch: bool = False
    seniority_stretch: bool = False
    working_rights_stated: bool = False
    portfolio_insufficient: bool = False
    insufficient_information: bool = False
    volume_enabled: bool = False
    material_commercial_conflicts: list[FitFinding] = field(default_factory=list)
    material_technical_gaps: list[FitFinding] = field(default_factory=list)


class DeterministicStrategyPlanner:
    """Explainable rule-based StrategyPlanner implementation."""

    def plan(
        self,
        assessment: OpportunityAssessment,
        portfolio_match: PortfolioMatch,
        profile: CareerProfile,
        operating_context: SearchOperatingContext,
    ) -> ApplicationStrategyPayload:
        signals = _extract_signals(
            assessment, portfolio_match, profile, operating_context
        )
        decision = _decide(signals)
        portfolio_emphasis = _build_portfolio_emphasis(portfolio_match, signals)
        reasons = _build_reasons(signals, decision)
        risks = _build_risks(signals, decision)
        manual_checks = _build_manual_checks(signals)
        assumptions = _build_assumptions(signals)
        decision_blockers = _build_decision_blockers(signals)
        next_actions = _build_next_actions(
            signals, decision, portfolio_emphasis, manual_checks
        )
        summary = _build_summary(signals, decision)

        return {
            "application_tier": decision.tier,
            "pursuit_posture": decision.posture,
            "practical_value": decision.practical_value,
            "effort_level": decision.resolved_effort,
            "summary": summary,
            "reasons": reasons,
            "risks_or_gaps": risks,
            "manual_checks": manual_checks,
            "next_actions": next_actions,
            "portfolio_emphasis": portfolio_emphasis,
            "assumptions": assumptions,
            "decision_blockers": decision_blockers,
            "owner_review_required": True,
            "insufficient_information": decision.posture == "insufficient_information",
        }


@dataclass(frozen=True)
class _Decision:
    posture: PursuitPosture
    tier: ApplicationTier
    practical_value: PracticalValue
    effort_level: EffortLevel | None = None

    @property
    def resolved_effort(self) -> EffortLevel:
        if self.effort_level is not None:
            return self.effort_level
        return _TIER_TO_EFFORT[self.tier]


def _extract_signals(
    assessment: OpportunityAssessment,
    portfolio_match: PortfolioMatch,
    profile: CareerProfile,
    operating_context: SearchOperatingContext,
) -> _Signals:
    job = assessment.job_analysis
    technical = assessment.technical_fit
    commercial = assessment.commercial_fit
    portfolio = assessment.portfolio_fit
    role_family = job.role_family.family

    ai_aligned = _is_ai_aligned(role_family, technical.judgment)
    outside = not ai_aligned

    employment_blocker = _employment_blocker(job, profile.preferences)
    salary_conflict, salary_unknown, salary_min_unset = _salary_signals(
        job, profile.preferences
    )
    location_mismatch, arrangement_mismatch = _location_signals(job, profile.preferences)
    seniority_stretch = _seniority_stretch(job, assessment, profile)
    working_rights_stated = _working_rights_stated(job, commercial)
    portfolio_insufficient = portfolio_match.insufficient_evidence or (
        not portfolio_match.ranked_projects
        and _judgment_rank(portfolio.judgment) <= _judgment_rank("weak")
    )

    material_commercial_conflicts = [
        finding
        for finding in commercial.findings
        if finding.kind == "conflict" and finding.importance == "material"
    ]
    material_technical_gaps = [
        finding
        for finding in technical.findings
        if finding.kind == "gap" and finding.importance == "material"
    ]

    insufficient = _is_insufficient(
        technical,
        commercial,
        portfolio,
        job,
        portfolio_match,
    )

    return _Signals(
        technical=technical,
        commercial=commercial,
        portfolio=portfolio,
        role_family=role_family,
        ai_aligned=ai_aligned,
        outside_ai_priority=outside,
        employment_blocker=employment_blocker,
        salary_conflict=salary_conflict,
        salary_unknown=salary_unknown,
        salary_min_unset=salary_min_unset,
        location_mismatch=location_mismatch,
        arrangement_mismatch=arrangement_mismatch,
        seniority_stretch=seniority_stretch,
        working_rights_stated=working_rights_stated,
        portfolio_insufficient=portfolio_insufficient,
        insufficient_information=insufficient,
        volume_enabled=operating_context.volume_applications_enabled,
        material_commercial_conflicts=material_commercial_conflicts,
        material_technical_gaps=material_technical_gaps,
    )


def _is_ai_aligned(role_family: str, technical_judgment: str) -> bool:
    if role_family in _AI_TARGET_FAMILIES:
        return True
    if role_family in _AI_ADJACENT_FAMILIES:
        return _judgment_rank(technical_judgment) >= _judgment_rank("mixed")
    return False


def _judgment_rank(judgment: str) -> int:
    return _JUDGMENT_RANK.get(judgment, 0)


def _employment_blocker(job: JobAnalysis, preferences: Preferences) -> str | None:
    preferred = list(preferences.employment_types)
    if not preferred:
        return None

    hours = job.employment.working_hours
    engagement = job.employment.engagement_type

    if "full_time" in preferred and "contract" not in preferred:
        if engagement == "contract":
            return (
                "Job engagement type is contract, but the profile preference is "
                "full-time only."
            )
        if engagement in {"casual", "internship"}:
            return (
                f"Job engagement type is {engagement}, which conflicts with the "
                "confirmed full-time preference."
            )
        if hours == "part_time":
            return (
                "Job working hours are part-time, which conflicts with the "
                "confirmed full-time preference."
            )

    if "part_time" in preferred and "full_time" not in preferred and hours == "full_time":
        return (
            "Job working hours are full-time, which conflicts with the confirmed "
            "part-time preference."
        )

    if preferred == ["contract"] and engagement not in {"contract", "unspecified"}:
        return (
            f"Job engagement type is {engagement}, which conflicts with the "
            "confirmed contract preference."
        )

    return None


def _salary_signals(
    job: JobAnalysis,
    preferences: Preferences,
) -> tuple[bool, bool, bool]:
    salary_min = preferences.salary_min
    salary_min_unset = salary_min is None
    compensation = job.compensation
    salary_unknown = compensation.clarity in {"unstated", "ambiguous"}

    if salary_min_unset or salary_unknown:
        return False, salary_unknown, salary_min_unset

    currency = preferences.salary_currency
    if (
        currency is not None
        and compensation.currency is not None
        and compensation.currency != currency
    ):
        # Different currency without conversion — treat as unknown, not invented conflict.
        return False, True, salary_min_unset

    maximum = compensation.maximum
    minimum = compensation.minimum
    if maximum is not None and maximum < salary_min:
        return True, False, salary_min_unset
    if maximum is None and minimum is not None and minimum < salary_min:
        return True, False, salary_min_unset
    return False, False, salary_min_unset


def _normalize_location_tokens(value: str) -> frozenset[str]:
    """Normalize a location string for deterministic soft geographic comparison."""
    text = value.casefold().strip()
    if not text:
        return frozenset()

    text = _PARENTHETICAL_RE.sub(" ", text)
    text = _LEADING_ARRANGEMENT_RE.sub("", text)
    text = _NON_ALNUM_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    for phrase, canonical in _STATE_PHRASE_ALIASES:
        text = text.replace(phrase, f" {canonical} ")

    text = _WHITESPACE_RE.sub(" ", text).strip()
    return frozenset(token for token in text.split(" ") if token)


def _locations_compatible(job_summary: str, preferred_location: str) -> bool:
    """Return True when job and preference locations are meaningfully compatible."""
    job_tokens = _normalize_location_tokens(job_summary)
    preferred_tokens = _normalize_location_tokens(preferred_location)
    if not job_tokens or not preferred_tokens:
        return False
    if job_tokens == preferred_tokens:
        return True
    # Prefer "Melbourne, VIC" against "Melbourne VIC (Hybrid)" / "Melbourne".
    if preferred_tokens <= job_tokens or job_tokens <= preferred_tokens:
        return True
    return False


def _location_signals(
    job: JobAnalysis,
    preferences: Preferences,
) -> tuple[bool, bool]:
    location_mismatch = False
    arrangement_mismatch = False

    preferred_locations = list(preferences.locations)
    remote_pref = preferences.remote
    arrangement = job.work_arrangement.arrangement

    if job.location.clarity == "stated" and job.location.summary and preferred_locations:
        location_match = any(
            _locations_compatible(job.location.summary, preferred)
            for preferred in preferred_locations
        )
        remote_pref_allows_remote = remote_pref in {"remote", "flexible"}
        remote_location_pref = any(
            "remote" in preferred.casefold() for preferred in preferred_locations
        )
        if not location_match:
            # Fully remote roles can satisfy remote/flexible preferences.
            if arrangement == "remote" and (
                remote_pref_allows_remote or remote_location_pref
            ):
                location_mismatch = False
            else:
                # Soft geographic mismatch — reduce priority, do not auto-reject.
                location_mismatch = True

    if arrangement != "unspecified":
        if remote_pref == "remote" and arrangement == "onsite":
            arrangement_mismatch = True
        elif remote_pref == "onsite" and arrangement == "remote":
            arrangement_mismatch = True
        elif remote_pref == "hybrid" and arrangement not in {"hybrid", "unspecified"}:
            if arrangement == "onsite":
                arrangement_mismatch = True
        # flexible: arrangement alone is not a hard mismatch.

    return location_mismatch, arrangement_mismatch


def _role_family_label(role_family: str) -> str:
    return _ROLE_FAMILY_LABELS.get(role_family, role_family.replace("_", " "))


def _role_family_reason_phrase(role_family: str) -> str:
    """Human-readable role-family phrase for strategy explanations.

    Only true AI-target families are labelled "AI-aligned". Adjacent families
    (e.g. software_engineering) keep their actual family name.
    """
    if role_family in _AI_TARGET_FAMILIES:
        return "AI-aligned role family"
    return f"{_role_family_label(role_family)} role family"


def _experience_blob(entry: object) -> str:
    parts: list[str] = [
        str(getattr(entry, "title", "")),
        str(getattr(entry, "organisation", "")),
    ]
    technologies = getattr(entry, "technologies", None) or []
    highlights = getattr(entry, "highlights", None) or []
    parts.extend(str(item) for item in technologies)
    parts.extend(str(item) for item in highlights)
    return " ".join(parts).casefold()


def _is_ai_related_experience(entry: object) -> bool:
    blob = _experience_blob(entry)
    return any(token in blob for token in _AI_ROLE_TOKENS)


def _has_senior_ownership_markers(entry: object) -> bool:
    blob = _experience_blob(entry)
    return any(token in blob for token in _SENIOR_OWNERSHIP_TOKENS)


def _has_direct_senior_commercial_ai_evidence(profile: CareerProfile) -> bool:
    """True when employment (not independent R&D) shows senior commercial AI ownership.

    Independent engineering and professional development support technical/portfolio
    fit but do not satisfy senior commercial AI employment evidence.
    """
    for entry in profile.experience:
        if entry.kind != "employment":
            continue
        if not _is_ai_related_experience(entry):
            continue
        if _has_senior_ownership_markers(entry):
            return True
    return False


def _finding_text(finding: FitFinding) -> str:
    return f"{finding.summary} {finding.detail or ''}".casefold()


def _finding_cites_seniority(finding: FitFinding) -> bool:
    return any(ref.source == "seniority" for ref in finding.job_evidence)


def _is_material_senior_commercial_gap(finding: FitFinding) -> bool:
    if finding.importance != "material":
        return False
    if finding.kind not in {"gap", "partial_alignment", "conflict"}:
        return False
    if _finding_cites_seniority(finding):
        return True
    blob = _finding_text(finding)
    return any(token in blob for token in _SENIOR_COMMERCIAL_GAP_TOKENS)


def _has_material_senior_commercial_gap(assessment: OpportunityAssessment) -> bool:
    for finding in (
        *assessment.commercial_fit.findings,
        *assessment.technical_fit.findings,
    ):
        if _is_material_senior_commercial_gap(finding):
            return True
    return False


def _job_text_blob(job: JobAnalysis) -> str:
    parts: list[str] = [job.posting.raw_text]
    if job.posting.title:
        parts.append(job.posting.title)
    for item in job.responsibilities:
        parts.append(item.description)
        for evidence in item.evidence:
            parts.append(evidence.excerpt)
    for item in job.experience_requirements:
        parts.append(item.description)
        for evidence in item.evidence:
            parts.append(evidence.excerpt)
    for evidence in job.seniority.evidence:
        parts.append(evidence.excerpt)
    return " ".join(parts).casefold()


def _token_matches(token: str, blob: str) -> bool:
    """Return True when ``token`` appears as a whole token/phrase in ``blob``.

    Prevents short tokens such as ``cto`` matching inside unrelated words
    (e.g. ``Victoria``). Multi-word phrases still match with word boundaries
    on each end.
    """
    pattern = rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])"
    return re.search(pattern, blob) is not None


def _job_expects_senior_commercial_leadership(job: JobAnalysis) -> bool:
    """True when the analysed job signals senior commercial / executive AI leadership."""
    blob = _job_text_blob(job)
    return any(_token_matches(token, blob) for token in _JOB_SENIOR_LEADERSHIP_TOKENS)


def _seniority_stretch(
    job: JobAnalysis,
    assessment: OpportunityAssessment,
    profile: CareerProfile,
) -> bool:
    """Detect explicit seniority mismatch for AI-target roles.

    Not a blanket ``senior => silver`` rule. Requires missing direct senior commercial
    AI employment evidence. For ``senior`` level, also requires either material OA
    senior/leadership/ownership gap findings or JobAnalysis text signalling senior
    commercial / executive leadership expectations. Salary-only commercial uncertainty
    alone does not trigger the cap.
    """
    role_family = job.role_family.family
    if role_family not in _AI_TARGET_FAMILIES:
        return False

    level = job.seniority.level
    if level == "unknown":
        return False
    if level not in _SENIOR_OR_ABOVE:
        return False

    if _has_direct_senior_commercial_ai_evidence(profile):
        return False

    # Lead / principal / manager without matching commercial AI evidence is a stretch.
    if level in _STRETCH_SENIORITY:
        return True

    # Explicit senior: findings-first, with JobAnalysis leadership signals as fallback
    # when Opportunity Assessment under-reports the gap (without changing FR-003).
    if assessment.commercial_fit.judgment == "strong":
        return False

    if _has_material_senior_commercial_gap(assessment):
        return True

    # Job-side senior commercial leadership expectation + missing employment evidence.
    # Does not fire for seniority title alone without leadership/executive language.
    return _job_expects_senior_commercial_leadership(job)


def _working_rights_stated(
    job: JobAnalysis,
    commercial: FitDimensionAssessment,
) -> bool:
    texts: list[str] = [job.posting.raw_text.casefold()]
    if job.location.summary:
        texts.append(job.location.summary.casefold())
    for item in job.experience_requirements:
        texts.append(item.description.casefold())
        for evidence in item.evidence:
            texts.append(evidence.excerpt.casefold())
    for finding in commercial.findings:
        texts.append(finding.summary.casefold())
        if finding.detail:
            texts.append(finding.detail.casefold())
        for job_ref in finding.job_evidence:
            if job_ref.excerpt:
                texts.append(job_ref.excerpt.casefold())

    blob = " ".join(texts)
    return any(token in blob for token in _WORKING_RIGHTS_TOKENS)


def _is_insufficient(
    technical: FitDimensionAssessment,
    commercial: FitDimensionAssessment,
    portfolio: FitDimensionAssessment,
    job: JobAnalysis,
    portfolio_match: PortfolioMatch,
) -> bool:
    if technical.judgment == "unknown":
        return True
    unknown_count = sum(
        1
        for judgment in (
            technical.judgment,
            commercial.judgment,
            portfolio.judgment,
        )
        if judgment == "unknown"
    )
    if unknown_count >= 2:
        return True
    if not job.technologies and not job.responsibilities:
        return True
    if portfolio_match.insufficient_evidence and technical.judgment == "unknown":
        return True
    return False


def _decide(signals: _Signals) -> _Decision:
    if signals.insufficient_information:
        return _Decision(
            posture="insufficient_information",
            tier="bronze",
            practical_value="deferred_pending_information",
        )

    if signals.employment_blocker is not None:
        return _Decision(
            posture="do_not_prioritise",
            tier="bronze",
            practical_value="acceptable_opportunity",
        )

    if signals.outside_ai_priority:
        if signals.volume_enabled:
            return _Decision(
                posture="low_effort_submit",
                tier="silver",
                practical_value="volume_obligation",
            )
        return _Decision(
            posture="do_not_prioritise",
            tier="bronze",
            practical_value="acceptable_opportunity",
        )

    tech = _judgment_rank(signals.technical.judgment)
    commercial = _judgment_rank(signals.commercial.judgment)
    portfolio = _judgment_rank(signals.portfolio.judgment)

    weak_overall = tech <= _judgment_rank("weak") and portfolio <= _judgment_rank("weak")
    if weak_overall:
        if signals.volume_enabled:
            return _Decision(
                posture="low_effort_submit",
                tier="silver",
                practical_value="volume_obligation",
            )
        return _Decision(
            posture="do_not_prioritise",
            tier="bronze",
            practical_value="acceptable_opportunity",
        )

    # Start from fit-based baseline for AI-aligned roles.
    if (
        tech >= _judgment_rank("strong")
        and portfolio >= _judgment_rank("strong")
        and commercial >= _judgment_rank("moderate")
        and not signals.seniority_stretch
        and not signals.salary_conflict
        and not signals.material_commercial_conflicts
    ):
        posture: PursuitPosture = "prioritise"
        tier: ApplicationTier = "platinum"
        practical: PracticalValue = "career_priority"
    elif tech >= _judgment_rank("strong") and commercial >= _judgment_rank("moderate"):
        posture = "pursue"
        tier = "gold"
        practical = "career_priority"
    elif tech >= _judgment_rank("moderate") and commercial >= _judgment_rank("mixed"):
        posture = "pursue"
        tier = "gold"
        practical = "career_priority"
    elif tech >= _judgment_rank("moderate"):
        posture = "consider"
        tier = "silver"
        practical = "acceptable_opportunity"
    else:
        posture = "consider"
        tier = "silver"
        practical = "acceptable_opportunity"

    # Strong technical + weak portfolio: do not auto-bronze.
    if tech >= _judgment_rank("strong") and portfolio <= _judgment_rank("weak"):
        posture = "pursue" if commercial >= _judgment_rank("moderate") else "consider"
        tier = "gold" if posture == "pursue" else "silver"
        practical = (
            "career_priority" if posture == "pursue" else "acceptable_opportunity"
        )

    # Mixed / weak commercial reductions.
    if commercial <= _judgment_rank("mixed") and posture == "prioritise":
        posture = "pursue"
        tier = "gold"
    if commercial <= _judgment_rank("weak") and posture in {"prioritise", "pursue"}:
        posture = "consider"
        tier = "silver"
        practical = "acceptable_opportunity"
    if signals.material_commercial_conflicts and posture == "prioritise":
        posture = "pursue"
        tier = "gold"

    # Seniority stretch: reduce and never claim prioritise.
    # Credible stretch (strong tech/portfolio) keeps targeted effort with Silver.
    if signals.seniority_stretch:
        if posture == "prioritise":
            posture = "pursue"
            tier = "gold"
            practical = "career_priority"
        elif posture == "pursue":
            posture = "consider"
            tier = "silver"
            practical = "acceptable_opportunity"
        else:
            posture = "consider"
            tier = "silver"
            practical = "acceptable_opportunity"

    # Salary conflict: material constraint / tier reduction.
    if signals.salary_conflict:
        if posture in {"prioritise", "pursue"}:
            posture = "consider"
            tier = "silver"
            practical = "acceptable_opportunity"
        elif posture == "consider":
            if signals.volume_enabled:
                posture = "low_effort_submit"
                tier = "silver"
                practical = "volume_obligation"
            else:
                posture = "do_not_prioritise"
                tier = "bronze"
                practical = "acceptable_opportunity"

    # Soft location / arrangement mismatch: reduce priority, do not auto-reject.
    if signals.location_mismatch or signals.arrangement_mismatch:
        if posture == "prioritise":
            posture = "pursue"
            tier = "gold"
        elif posture == "pursue":
            posture = "consider"
            tier = "silver"
            practical = "acceptable_opportunity"

    # Commercial misaligned without employment blocker: deprioritise unless volume.
    if signals.commercial.judgment == "misaligned":
        if signals.volume_enabled:
            return _Decision(
                posture="low_effort_submit",
                tier="silver",
                practical_value="volume_obligation",
            )
        return _Decision(
            posture="do_not_prioritise",
            tier="bronze",
            practical_value="acceptable_opportunity",
        )

    effort: EffortLevel | None = None
    if (
        signals.seniority_stretch
        and posture == "consider"
        and tier == "silver"
        and tech >= _judgment_rank("strong")
        and portfolio >= _judgment_rank("strong")
    ):
        # Stretch senior AI roles with strong capability evidence warrant targeted
        # attention without Gold pursuit priority.
        effort = "targeted"

    return _Decision(
        posture=posture,
        tier=tier,
        practical_value=practical,
        effort_level=effort,
    )


def _assessment_evidence(dimension: str, judgment: str) -> dict[str, Any]:
    return {
        "origin": "opportunity_assessment",
        "assessment_dimension": dimension,
        "assessment_judgment": judgment,
    }


def _job_evidence(
    source: str,
    *,
    item_index: int | None = None,
    name: str | None = None,
    excerpt: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "origin": "job_analysis",
        "job_evidence": {"source": source},
    }
    job_ref: dict[str, Any] = payload["job_evidence"]
    if item_index is not None:
        job_ref["item_index"] = item_index
    if name is not None:
        job_ref["name"] = name
    if excerpt is not None:
        job_ref["excerpt"] = excerpt
    return payload


def _profile_evidence(source: str, ref: str) -> dict[str, Any]:
    return {
        "origin": "career_profile",
        "profile_evidence": {"source": source, "ref": ref},
    }


def _portfolio_evidence(project_id: str) -> dict[str, Any]:
    return {
        "origin": "portfolio_match",
        "portfolio_project_id": project_id,
    }


def _build_portfolio_emphasis(
    portfolio_match: PortfolioMatch,
    signals: _Signals,
) -> list[dict[str, Any]]:
    if signals.portfolio_insufficient or not portfolio_match.ranked_projects:
        return []

    emphasis: list[dict[str, Any]] = []
    for entry in portfolio_match.ranked_projects[:_MAX_PORTFOLIO_EMPHASIS]:
        emphasis.append(
            {
                "project_id": entry.project_id,
                "source_rank": entry.rank,
                "summary": (
                    f"Consider emphasising '{entry.project_id}' "
                    f"(PortfolioMatch rank {entry.rank})."
                ),
                "evidence": [_portfolio_evidence(entry.project_id)],
            }
        )
    return emphasis


def _build_reasons(signals: _Signals, decision: _Decision) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []

    if decision.posture == "insufficient_information":
        reasons.append(
            {
                "kind": "uncertainty",
                "summary": (
                    "Available job and fit evidence is insufficient for a confident "
                    "application strategy."
                ),
                "importance": "material",
                "evidence": [
                    _assessment_evidence("technical", signals.technical.judgment)
                ],
            }
        )
        return reasons

    if signals.employment_blocker:
        reasons.append(
            {
                "kind": "constraint",
                "summary": signals.employment_blocker,
                "importance": "material",
                "evidence": [
                    _job_evidence("employment"),
                    _profile_evidence("preference", "preference:employment_types"),
                ],
            }
        )
        return reasons

    if decision.practical_value == "volume_obligation":
        reasons.append(
            {
                "kind": "practical_value",
                "summary": (
                    "Strategic fit is limited, but volume applications are enabled; "
                    "a low-effort application may still be reasonable for the owner."
                ),
                "importance": "material",
                "evidence": [
                    _assessment_evidence("technical", signals.technical.judgment),
                    _assessment_evidence("commercial", signals.commercial.judgment),
                ],
            }
        )
        reasons.append(
            {
                "kind": "priority",
                "summary": (
                    f"Role family '{signals.role_family}' is outside the current "
                    "AI Engineering priority set for significant effort."
                    if signals.outside_ai_priority
                    else "Overall fit does not justify significant application effort."
                ),
                "importance": "material",
                "evidence": [
                    _job_evidence("role_family")
                    if signals.outside_ai_priority
                    else _assessment_evidence("technical", signals.technical.judgment)
                ],
            }
        )
        return reasons

    if signals.outside_ai_priority:
        reasons.append(
            {
                "kind": "priority",
                "summary": (
                    f"Role family '{signals.role_family}' is outside the owner's "
                    "current AI Engineering target set and is not recommended for "
                    "significant effort."
                ),
                "importance": "material",
                "evidence": [_job_evidence("role_family")],
            }
        )
        return reasons

    reasons.append(
        {
            "kind": "alignment",
            "summary": (
                f"Technical fit is '{signals.technical.judgment}' and portfolio fit "
                f"is '{signals.portfolio.judgment}' for this opportunity."
            ),
            "importance": "material",
            "evidence": [
                _assessment_evidence("technical", signals.technical.judgment),
                _assessment_evidence("portfolio", signals.portfolio.judgment),
            ],
        }
    )

    if signals.seniority_stretch:
        reasons.append(
            {
                "kind": "constraint",
                "summary": (
                    "Strong technical and portfolio alignment make this a credible "
                    "stretch role, but the position is explicitly senior and the "
                    "profile does not yet demonstrate matching senior commercial AI "
                    f"ownership. Recommend {decision.posture} / {decision.tier} with "
                    f"{decision.resolved_effort} effort."
                ),
                "importance": "material",
                "evidence": [
                    _job_evidence("seniority"),
                    _assessment_evidence("commercial", signals.commercial.judgment),
                ],
            }
        )
    else:
        reasons.append(
            {
                "kind": "priority",
                "summary": (
                    f"Pursuit posture '{decision.posture}' with effort tier "
                    f"'{decision.tier}' reflects commercial fit "
                    f"'{signals.commercial.judgment}' and "
                    f"{_role_family_reason_phrase(signals.role_family)}."
                ),
                "importance": "material",
                "evidence": [
                    _assessment_evidence("commercial", signals.commercial.judgment),
                    _job_evidence("role_family"),
                ],
            }
        )

    if decision.tier in {"platinum", "gold"} or (
        signals.seniority_stretch and decision.resolved_effort == "targeted"
    ):
        reasons.append(
            {
                "kind": "effort",
                "summary": (
                    f"Effort level '{decision.resolved_effort}' is justified "
                    f"by the current fit evidence for this "
                    f"{_role_family_label(signals.role_family)} opportunity."
                ),
                "importance": "minor",
                "evidence": [
                    _assessment_evidence("technical", signals.technical.judgment)
                ],
            }
        )

    return reasons


def _build_risks(signals: _Signals, decision: _Decision) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []

    if signals.seniority_stretch:
        risks.append(
            {
                "summary": (
                    "Explicit seniority and commercial AI leadership requirements "
                    "are not fully evidenced in the profile. Technical capability "
                    "and portfolio evidence remain distinct from senior commercial "
                    "AI employment ownership."
                ),
                "importance": "material",
                "evidence": [
                    _job_evidence("seniority"),
                    _assessment_evidence("commercial", signals.commercial.judgment),
                ],
            }
        )

    if signals.portfolio_insufficient:
        risks.append(
            {
                "summary": (
                    "Portfolio evidence is weak or insufficient for ranked emphasis, "
                    "even if technical fit remains usable."
                ),
                "importance": "material",
                "evidence": [
                    _assessment_evidence("portfolio", signals.portfolio.judgment)
                ],
            }
        )
    elif _judgment_rank(signals.portfolio.judgment) <= _judgment_rank("weak"):
        risks.append(
            {
                "summary": (
                    "Portfolio fit is limited relative to the role; emphasise only "
                    "honest project evidence."
                ),
                "importance": "material",
                "evidence": [
                    _assessment_evidence("portfolio", signals.portfolio.judgment)
                ],
            }
        )

    if signals.salary_conflict:
        risks.append(
            {
                "summary": (
                    "Stated compensation appears below the confirmed salary minimum."
                ),
                "importance": "material",
                "evidence": [
                    _job_evidence("compensation"),
                    _profile_evidence("preference", "preference:salary_min"),
                ],
            }
        )

    if signals.location_mismatch or signals.arrangement_mismatch:
        risks.append(
            {
                "summary": (
                    "Location or work-arrangement signals conflict with confirmed "
                    "preferences; treat as a soft constraint unless the owner accepts it."
                ),
                "importance": "material"
                if signals.arrangement_mismatch and signals.location_mismatch
                else "minor",
                "evidence": [
                    _job_evidence("location")
                    if signals.location_mismatch
                    else _job_evidence("work_arrangement"),
                    _profile_evidence("preference", "preference:locations")
                    if signals.location_mismatch
                    else _profile_evidence("preference", "preference:remote"),
                ],
            }
        )

    if _judgment_rank(signals.commercial.judgment) <= _judgment_rank("mixed"):
        if decision.posture not in {"do_not_prioritise", "insufficient_information"}:
            risks.append(
                {
                    "summary": (
                        f"Commercial fit is '{signals.commercial.judgment}', which "
                        "may reduce the value of investing significant effort."
                    ),
                    "importance": "material"
                    if _judgment_rank(signals.commercial.judgment)
                    <= _judgment_rank("weak")
                    else "minor",
                    "evidence": [
                        _assessment_evidence("commercial", signals.commercial.judgment)
                    ],
                }
            )

    for finding in signals.material_technical_gaps[:2]:
        risks.append(
            {
                "summary": finding.summary,
                "importance": "material",
                "evidence": [
                    _assessment_evidence("technical", signals.technical.judgment)
                ],
            }
        )

    return risks


def _build_manual_checks(signals: _Signals) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    if signals.insufficient_information:
        checks.append(
            {
                "summary": "Gather missing job requirements and commercial details.",
                "why_it_matters": (
                    "Additional posting detail could change pursuit posture and effort."
                ),
                "could_change_recommendation": True,
                "evidence": [
                    _assessment_evidence("technical", signals.technical.judgment)
                ],
            }
        )

    if signals.salary_unknown:
        checks.append(
            {
                "summary": "Review compensation once salary or rate information is available.",
                "why_it_matters": (
                    "Compensation clarity can change commercial priority; no salary "
                    "conflict was invented from missing data."
                ),
                "could_change_recommendation": True,
                "evidence": [_job_evidence("compensation")],
            }
        )
    elif signals.salary_conflict:
        checks.append(
            {
                "summary": "Confirm whether the stated compensation is acceptable.",
                "why_it_matters": (
                    "A confirmed salary minimum conflict may justify deprioritising "
                    "significant effort."
                ),
                "could_change_recommendation": True,
                "evidence": [
                    _job_evidence("compensation"),
                    _profile_evidence("preference", "preference:salary_min"),
                ],
            }
        )

    if signals.working_rights_stated:
        checks.append(
            {
                "summary": "Verify working-rights wording against your own eligibility.",
                "why_it_matters": (
                    "The posting states a working-rights requirement; the system does "
                    "not infer owner eligibility."
                ),
                "could_change_recommendation": True,
                "evidence": [
                    _assessment_evidence("commercial", signals.commercial.judgment)
                ],
            }
        )

    if signals.seniority_stretch:
        checks.append(
            {
                "summary": "Review seniority expectations against demonstrated experience.",
                "why_it_matters": (
                    "A seniority stretch can change whether significant effort is justified."
                ),
                "could_change_recommendation": True,
                "evidence": [_job_evidence("seniority")],
            }
        )

    if signals.location_mismatch or signals.arrangement_mismatch:
        checks.append(
            {
                "summary": "Review location and work-arrangement expectations.",
                "why_it_matters": (
                    "Soft location mismatches should be accepted consciously by the owner."
                ),
                "could_change_recommendation": True,
                "evidence": [
                    _job_evidence("location")
                    if signals.location_mismatch
                    else _job_evidence("work_arrangement")
                ],
            }
        )

    return checks


def _build_assumptions(signals: _Signals) -> list[str]:
    assumptions: list[str] = []
    if signals.salary_unknown:
        assumptions.append(
            "Compensation fit is not scored because salary/rate evidence is missing "
            "or ambiguous."
        )
    if signals.salary_min_unset and not signals.salary_conflict:
        assumptions.append(
            "No candidate salary minimum is configured, so compensation was not "
            "treated as a hard threshold conflict."
        )
    if signals.working_rights_stated:
        assumptions.append(
            "Owner working-rights eligibility is unknown to the system and was not inferred."
        )
    if signals.volume_enabled and signals.outside_ai_priority:
        assumptions.append(
            "Volume applications are enabled; low strategic fit may still justify "
            "minimal-effort submission by owner choice."
        )
    return assumptions


def _build_decision_blockers(signals: _Signals) -> list[str]:
    if signals.employment_blocker:
        return [signals.employment_blocker]
    return []


def _build_next_actions(
    signals: _Signals,
    decision: _Decision,
    portfolio_emphasis: list[dict[str, Any]],
    manual_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    def _add(kind: str, summary: str, evidence: list[dict[str, Any]], **extra: Any) -> None:
        if len(actions) >= _MAX_NEXT_ACTIONS:
            return
        if any(action["kind"] == kind for action in actions):
            return
        payload: dict[str, Any] = {
            "kind": kind,
            "summary": summary,
            "evidence": evidence,
        }
        payload.update(extra)
        actions.append(payload)

    if decision.posture == "insufficient_information":
        _add(
            "consider_gathering_missing_job_information",
            "Consider gathering missing job information before deciding effort.",
            [_assessment_evidence("technical", signals.technical.judgment)],
        )

    if signals.working_rights_stated:
        _add(
            "consider_verifying_working_rights",
            "Consider verifying working-rights wording against your eligibility.",
            [_assessment_evidence("commercial", signals.commercial.judgment)],
        )

    if signals.salary_unknown or signals.salary_conflict:
        _add(
            "consider_reviewing_compensation",
            "Consider reviewing compensation before investing significant effort.",
            [_job_evidence("compensation")],
        )

    if signals.seniority_stretch:
        _add(
            "consider_reviewing_seniority_expectations",
            "Consider reviewing seniority expectations against demonstrated experience.",
            [_job_evidence("seniority")],
        )

    if signals.location_mismatch or signals.arrangement_mismatch:
        _add(
            "consider_reviewing_location_or_arrangement",
            "Consider reviewing location or work-arrangement expectations.",
            [
                _job_evidence("location")
                if signals.location_mismatch
                else _job_evidence("work_arrangement")
            ],
        )

    if portfolio_emphasis:
        lead = portfolio_emphasis[0]
        _add(
            "consider_emphasising_portfolio_projects",
            (
                "Consider emphasising the strongest matched portfolio project(s) "
                "in any application materials you prepare."
            ),
            [_portfolio_evidence(str(lead["project_id"]))],
            related_project_id=lead["project_id"],
        )

    if decision.tier in {"platinum", "gold"}:
        _add(
            "consider_cv_tailoring",
            "Consider whether CV tailoring is worth the effort for this opportunity.",
            [_assessment_evidence("technical", signals.technical.judgment)],
        )
        if decision.tier == "platinum" and len(actions) < _MAX_NEXT_ACTIONS:
            _add(
                "consider_cover_letter",
                "Consider whether a cover letter is worth preparing for this opportunity.",
                [_assessment_evidence("technical", signals.technical.judgment)],
            )

    if decision.posture == "low_effort_submit":
        _add(
            "consider_low_effort_application",
            "Consider a low-effort application if you choose to submit for volume reasons.",
            [_assessment_evidence("technical", signals.technical.judgment)],
        )

    if decision.posture == "do_not_prioritise" or decision.tier == "bronze":
        _add(
            "consider_logging_and_deprioritising",
            "Consider logging the rationale and not investing significant effort.",
            [_assessment_evidence("technical", signals.technical.judgment)],
        )

    _add(
        "consider_owner_review",
        "Consider reviewing this full strategy before taking any external action.",
        [_assessment_evidence("technical", signals.technical.judgment)],
    )

    # Keep next_actions grounded in the five-question standard without exceeding cap.
    _ = manual_checks
    return actions[:_MAX_NEXT_ACTIONS]


def _build_summary(signals: _Signals, decision: _Decision) -> str:
    effort = decision.resolved_effort
    if decision.posture == "insufficient_information":
        return (
            "Insufficient information for a confident strategy; gather missing details "
            "before investing significant application effort."
        )
    if decision.posture == "low_effort_submit":
        return (
            "Strategic fit is limited. If volume applications are desired, consider a "
            f"low-effort submission (tier {decision.tier}, effort {effort}). "
            "This is a recommendation only; the owner decides whether to apply."
        )
    if decision.posture == "do_not_prioritise":
        return (
            f"Do not prioritise significant effort for this opportunity "
            f"(tier {decision.tier}, effort {effort}). Bronze means low effort "
            "investment guidance, not an automatic never-apply decision."
        )
    if signals.seniority_stretch:
        return (
            f"Recommend posture '{decision.posture}' with effort tier '{decision.tier}' "
            f"({effort}). Technical fit '{signals.technical.judgment}' and portfolio fit "
            f"'{signals.portfolio.judgment}' support a credible stretch, but explicit "
            f"seniority with commercial fit '{signals.commercial.judgment}' lacks matching "
            "senior commercial AI employment evidence. Owner review is required before "
            "any application action."
        )
    return (
        f"Recommend posture '{decision.posture}' with effort tier '{decision.tier}' "
        f"({effort}). Technical fit '{signals.technical.judgment}', commercial fit "
        f"'{signals.commercial.judgment}', portfolio fit '{signals.portfolio.judgment}'. "
        "Owner review is required before any application action."
    )
