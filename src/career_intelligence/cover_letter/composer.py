"""Deterministic cover letter prose composition from an approved plan.

The planner selects evidence; this module writes human letter prose.
Planner vocabulary must never appear in the finished document.
"""

from __future__ import annotations

import re

from career_intelligence.profile.models import CareerProfile, Project

from .models import CoverLetterPlan, StrongestProject
from .opening_strategies import (
    lead_project_name,
    leading_technologies,
    select_opening_strategy,
)
from .project_eli10 import project_narrative

_FORBIDDEN_PHRASES = (
    "i am writing to apply",
    "i am excited to apply",
    "i am thrilled",
    "i wish to apply",
    "please find attached",
    "dear sir or madam",
    "to whom it may concern",
    "i believe i would be a perfect fit",
    "leverage synergies",
    "passionate about leveraging",
    "i am passionate",
    "i am excited",
    "i have always wanted",
    "i've always wanted",
    "dream role",
    "shaping the future",
    "furthermore",
    "moreover",
    "in today's rapidly evolving",
    "not only",
    "world-class",
    "industry-leading",
    "the business value is",
    "this demonstrates",
    "maps directly",
    # Planner / assessment vocabulary — must not leak into the letter.
    "most relevant portfolio evidence",
    "relevant evidence",
    "role alignment",
    "strongest project",
    "opportunity assessment",
    "planned portfolio",
    "application strategy",
    "the brief emphasises",
    "the brief focuses",
    "the role emphasises",
    "my background is directly relevant",
    "alignment_hook",
    "portfolio evidence includes",
    "demonstrates operational intelligence capability",
    "selection_reason",
    "fit_focus",
)

_PORTFOLIO_BODY_ROLE_FAMILIES = frozenset(
    {
        "ai_engineering",
        "ai_adjacent",
        "ai_solutions",
        "ml_engineering",
        "software_engineering",
        "data_engineering",
    }
)

_MARKETING_FLUFF = (
    "shaping the future of",
    "shaping the future",
    "the future of",
    "cutting-edge",
    "world-class",
    "best-in-class",
    "next-generation of",
    "revolutionising",
    "revolutionizing",
)

_STAKEHOLDER_CUES = (
    "stakeholder",
    "stakeholders",
    "uat",
    "user acceptance",
    "adoption",
    "business requirement",
    "business requirements",
    "non-technical",
    "communicate",
    "communication",
    "workshop",
    "translate requirements",
    "translating",
)

_IMPERATIVE_TO_GERUND = {
    "build": "building",
    "operate": "operating",
    "design": "designing",
    "develop": "developing",
    "deploy": "deploying",
    "contribute": "contributing",
    "deliver": "delivering",
    "create": "creating",
    "implement": "implementing",
    "lead": "leading",
    "drive": "driving",
    "own": "owning",
    "support": "supporting",
    "enable": "enabling",
    "scale": "scaling",
    "improve": "improving",
    "partner": "partnering",
    "work": "working",
    "help": "helping",
    "shape": "shaping",
    "embed": "embedding",
    "bring": "bringing",
    "turn": "turning",
    "make": "making",
    "ensure": "ensuring",
    "maintain": "maintaining",
    "monitor": "monitoring",
    "test": "testing",
    "validate": "validating",
    "integrate": "integrating",
    "automate": "automating",
    "learn": "learning",
    "collaborate": "collaborating",
    "reengineer": "reengineering",
    "optimize": "optimizing",
    "optimise": "optimising",
    "evaluate": "evaluating",
    "ship": "shipping",
}

_THIRD_PERSON_TO_BASE = {
    "designs": "design",
    "builds": "build",
    "evaluates": "evaluate",
    "operates": "operate",
    "creates": "create",
    "delivers": "deliver",
    "develops": "develop",
    "deploys": "deploy",
    "leads": "lead",
    "drives": "drive",
    "owns": "own",
    "supports": "support",
    "enables": "enable",
    "shapes": "shape",
    "embeds": "embed",
    "learns": "learn",
    "contributes": "contribute",
    "ships": "ship",
}


def compose_cover_letter_paragraphs(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None = None,
) -> list[str]:
    """Compose ~1-page recruiter-ready paragraphs from the approved plan."""
    company = plan.company_alignment.company
    role = plan.role_motivation.role_title
    employer = _employer_voice(plan)

    opening = _compose_opening(plan, profile, company, role, employer=employer)
    motivation = _compose_motivation(plan, profile, company, employer=employer)
    project_paragraphs = _compose_project_paragraphs(plan, profile, contact=contact)
    portfolio_note = _compose_portfolio_body_note(plan, contact=contact)
    closing = _compose_closing(plan, company, role, employer=employer)

    paragraphs = [opening, motivation, *project_paragraphs]
    if portfolio_note:
        paragraphs.append(portfolio_note)
    paragraphs.append(closing)
    # Keep within CoverLetter schema (max 5): merge trailing projects if needed.
    if len(paragraphs) > 5:
        head = paragraphs[:2]
        middle = paragraphs[2:-1]
        closing_part = paragraphs[-1]
        merged_middle = " ".join(middle)
        paragraphs = [*head, merged_middle, closing_part]

    validated = [
        _strip_ai_punctuation(_clamp_sentence_spacing(part))
        for part in paragraphs
        if part.strip()
    ]
    plain = " ".join(validated).casefold()
    if any(phrase in plain for phrase in _FORBIDDEN_PHRASES):
        return _fallback_paragraphs(plan, profile, contact=contact)
    if "—" in " ".join(validated) or "–" in " ".join(validated):
        return _fallback_paragraphs(plan, profile, contact=contact)
    if not _letter_quality_ok(validated, employer=employer):
        return _fallback_paragraphs(plan, profile, contact=contact)
    return validated


def _employer_voice(plan: CoverLetterPlan) -> dict[str, str]:
    """Recruiter vs employer phrasing when the hiring company is unknown."""
    company = (plan.company_alignment.company or "").strip()
    raw = (plan.job_analysis.posting.raw_text or "").casefold()
    company_folded = company.casefold()
    recruiter_name_markers = (
        "recruitment",
        "recruiter",
        "talent",
        "staffing",
        "search firm",
        "personnel",
    )
    is_recruiter = any(marker in company_folded for marker in recruiter_name_markers)
    client_cues = (
        "our client",
        "on behalf of",
        "client organisation",
        "client organization",
        "for our client",
    )
    mentions_client = any(cue in raw for cue in client_cues)
    if not is_recruiter and not mentions_client:
        return {
            "mode": "direct",
            "opening_subject": f"{_possessive(company)} {plan.role_motivation.role_title} role",
            "challenge_owner": f"{_possessive(company)} technical challenges",
            "closing_role": f"the {plan.role_motivation.role_title} role at {company}",
            "contribution_role": f"{_possessive(company)} {plan.role_motivation.role_title} work",
        }
    return {
        "mode": "recruiter",
        "opening_subject": (
            f"the {plan.role_motivation.role_title} role advertised through {company}"
        ),
        "challenge_owner": "your client's technical challenges",
        "closing_role": (
            f"the {plan.role_motivation.role_title} role with your client"
        ),
        "contribution_role": (
            f"the {plan.role_motivation.role_title} work with your client"
        ),
    }


def _possessive(name: str) -> str:
    cleaned = name.strip()
    if cleaned.casefold().endswith("s"):
        return f"{cleaned}'"
    return f"{cleaned}'s"


def _compose_opening(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    company: str,
    role: str,
    *,
    employer: dict[str, str],
) -> str:
    """Deterministic opening chosen from role, employer, evidence, and profile."""
    attraction = _scrub_marketing(_clean_phrase(plan.company_alignment.alignment_hook))
    themes = _scrub_marketing(_clean_phrase(plan.role_motivation.motivation))

    primary = attraction
    secondary = themes
    if _is_weak_attraction(primary) and secondary:
        primary, secondary = secondary, attraction
    if _is_recruiting_noun_phrase(primary) and secondary:
        primary, secondary = secondary, ""

    chance = _as_chance_clause(primary)
    strategy = select_opening_strategy(
        plan, profile, employer_mode=employer["mode"]
    )
    subject = employer["opening_subject"]
    subject_cap = _capitalize_phrase(subject)

    if strategy == "technology_led":
        techs = leading_technologies(plan, limit=3)
        tech_phrase = _oxford_join(techs) if techs else "production AI delivery"
        return (
            f"The {role} brief around {tech_phrase} matches how I design and ship "
            f"production systems. For {subject}, I want to {chance}."
        )

    if strategy == "business_problem_led":
        problem = _as_gerund_phrase(secondary or primary, limit=90)
        # Avoid restating the same clause as both problem and chance.
        if problem and _same_delivery_theme(problem, chance):
            return (
                f"{subject_cap} is ultimately about {problem}. That is the kind of "
                "delivery problem I want to own next."
            )
        return (
            f"{subject_cap} is ultimately about {problem}. That is the kind of "
            f"delivery problem I want to own: {chance}."
        )

    if strategy == "organisation_led":
        org = company.strip() or "the hiring organisation"
        if employer["mode"] == "recruiter":
            org_line = (
                f"The advertised organisation is hiring for production AI delivery "
                f"with real operational constraints."
            )
        else:
            org_line = (
                f"What stands out about {org} is the focus on shipping useful systems "
                f"under real delivery pressure."
            )
        return (
            f"{org_line} {subject_cap} is a chance to {chance}."
        )

    if strategy == "career_transition_led":
        years = _independent_portfolio_years(profile)
        return (
            f"After 3.5 years of commercial Data Engineering and the past {years} "
            f"building independent AI systems, {subject} is a natural next step: "
            f"{chance}."
        )

    if strategy == "mission_capability_led":
        return (
            "I look for roles where AI systems have to stay reviewable under real "
            f"operational pressure. {subject_cap} fits that bar: {chance}."
        )

    # experience_led (default)
    project = lead_project_name(plan)
    if project:
        return (
            f"Recent work on {project} and related production-style AI systems is "
            f"directly relevant to {subject}. I want to {chance}."
        )
    return (
        f"Recent production-style AI engineering work is a strong fit for {subject}. "
        f"I want to {chance}."
    )


def _capitalize_phrase(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    if cleaned[:3].isupper() or cleaned.startswith(("LLM", "RAG", "API", "AI ")):
        return cleaned
    return cleaned[0].upper() + cleaned[1:]


def _same_delivery_theme(left: str, right: str) -> bool:
    """True when two chance/problem phrases describe the same delivery theme."""
    def _norm(value: str) -> str:
        text = value.casefold()
        for gerund, base in (
            ("designing", "design"),
            ("building", "build"),
            ("deploying", "deploy"),
            ("developing", "develop"),
            ("evaluating", "evaluate"),
            ("operating", "operate"),
            ("delivering", "deliver"),
            ("creating", "create"),
            ("implementing", "implement"),
        ):
            text = text.replace(gerund, base)
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    a = _norm(left)
    b = _norm(right)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _oxford_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _compose_motivation(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    company: str,
    *,
    employer: dict[str, str],
) -> str:
    """Credibility, portfolio breadth, philosophy, and collaboration."""
    del company
    years = _independent_portfolio_years(profile)
    breadth = (
        f"Over the past {years} I have built a portfolio of production-style AI "
        "engineering projects spanning intelligent document search, operational "
        "analytics, AI governance and career intelligence systems."
    )
    craft = (
        "I build with an architecture-first mindset. "
        "I keep logic deterministic where that is the right tool, validate with "
        "evidence, and keep a human in the loop where the stakes require it. "
        "I favour explainable, production-quality systems over opaque model responses."
    )
    collaboration = (
        "I work well with engineers on design reviews, trade-offs and delivery "
        "sequencing, and I am comfortable explaining technical decisions clearly."
    )
    stakeholder = ""
    if _jd_mentions_stakeholders(plan):
        stakeholder = (
            " I also translate business requirements into practical AI systems "
            "and support adoption with concrete demos rather than slideware."
        )
    return (
        f"{_credibility_claim_short(profile)}. {breadth} {craft} "
        f"{collaboration}{stakeholder} "
        f"That is the approach I would bring to {employer['challenge_owner']}."
    )


def _compose_project_paragraphs(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None,
) -> list[str]:
    """One short paragraph per selected project, with varied structures."""
    projects = list(plan.strongest_projects[:3])
    if not projects:
        return []

    portfolio_lead = _portfolio_lead(contact, count=len(projects))
    by_id = {project.id: project for project in profile.projects}
    fingerprint = (
        f"{plan.company_alignment.company}|{plan.role_motivation.role_title}"
    )
    paragraphs: list[str] = []
    for index, project in enumerate(projects):
        structure = _project_structure_index(
            fingerprint, project.project_id, index
        )
        block = _project_block(
            project,
            by_id.get(project.project_id),
            structure=structure,
            is_lead=(index == 0),
        )
        if index == 0:
            paragraphs.append(f"{portfolio_lead} {block}")
        else:
            paragraphs.append(block)
    return paragraphs


def _project_structure_index(fingerprint: str, project_id: str, index: int) -> int:
    """Stable 0..2 structure choice — same inputs always yield the same rhythm."""
    seed = sum(ord(char) for char in f"{fingerprint}|{project_id}") + (index * 17)
    return seed % 3


def _compose_projects(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None,
) -> str | None:
    """Fallback single-block project section (used by emergency fallback path)."""
    parts = _compose_project_paragraphs(plan, profile, contact=contact)
    if not parts:
        return None
    return " ".join(parts)


def _project_block(
    project: StrongestProject,
    profile_project: Project | None,
    *,
    structure: int,
    is_lead: bool = False,
) -> str:
    """Project paragraph with deterministic structural variation."""
    narrative = project_narrative(
        project_id=project.project_id,
        project_name=project.project_name,
        profile_project=profile_project,
        emphasis=project.emphasis,
        business_outcome=project.business_outcome,
        fit_focus=project.fit_focus,
    )
    name = project.project_name
    does = narrative.does.strip()
    engineering = narrative.engineering.strip().rstrip(".")
    outcome = narrative.outcome.strip().rstrip(".")
    bridge = _role_relevance_bridge(project.fit_focus)

    style = structure % 3
    if style == 0:
        # Problem → architecture → outcome
        body = (
            f"{name} addresses a concrete delivery need: it {does}. "
            f"The architecture centres on {engineering}. "
            f"Result: {outcome}."
        )
    elif style == 1:
        # Business need → technical solution → business value
        if is_lead:
            body = (
                f"{name} solves a clear business need: it {does}, with design "
                f"decisions around {engineering}. In practice, {outcome}."
            )
        else:
            body = (
                f"Another useful example is {name}. "
                f"It {does}, with design decisions around {engineering}. "
                f"In practice, {outcome}."
            )
    else:
        # Challenge → design decisions → result
        lead = name if is_lead else f"I would also point to {name}"
        if is_lead:
            body = (
                f"{name} is a useful reference here. The engineering challenge is "
                f"keeping the system reviewable while it {does}. Design decisions "
                f"centre on {engineering}. If useful, I can walk through the working "
                "software and the trade-offs behind it."
            )
        else:
            body = (
                f"{lead}. "
                f"The engineering challenge is keeping the system reviewable while it "
                f"{does}. Design decisions centre on {engineering}. "
                f"If useful, I can walk through the working software and the trade-offs "
                "behind it."
            )
    if bridge and style != 2:
        return f"{body} {bridge}"
    return body


def _compose_portfolio_body_note(
    plan: CoverLetterPlan,
    *,
    contact: dict[str, str] | None,
) -> str | None:
    """Natural body reference to portfolio/GitHub for engineering role families."""
    family = plan.job_analysis.role_family.family
    if family not in _PORTFOLIO_BODY_ROLE_FAMILIES:
        return None
    if not plan.strongest_projects:
        return None
    display = _portfolio_display(contact)
    if display:
        return (
            "Working demonstrations and architecture notes for the systems above "
            f"are on my portfolio ({display}), together with matching GitHub "
            "repositories. Those artefacts matter when you want to inspect delivery "
            "decisions rather than slideware."
        )
    return (
        "Working demonstrations, architecture notes and GitHub repositories for "
        "the systems above are available in my portfolio. Those artefacts matter "
        "when you want to inspect delivery decisions rather than slideware."
    )


def _role_relevance_bridge(fit_focus: str | None) -> str:
    """Connect project capability to the advertised role without planner jargon."""
    cleaned = _scrub_marketing(_clean_phrase(fit_focus or ""))
    if len(cleaned) < 24:
        return ""
    # Prefer a complete first capability clause — avoid mid-list truncation.
    clause = cleaned
    for separator in ("; ", " and ", ", "):
        at = cleaned.find(separator)
        if at >= 28:
            clause = cleaned[:at].strip()
            break
    short = _truncate_words(clause, limit=88)
    # Keep bridges to a single capability clause (avoid mid-list fragments).
    if "," in short:
        short = short.split(",", 1)[0].strip()
    if len(short) < 20:
        return ""
    dangling = (" structured", " including", " with", " and", " for", " to")
    if short.casefold().endswith(dangling):
        return ""
    # Preserve leading acronyms (LLM, RAG, API); otherwise sentence-case.
    if short[:3].isupper() or short.startswith(("LLM", "RAG", "API", "AI ")):
        display = short
    else:
        display = short[0].lower() + short[1:]
    return f"That is useful for teams that need {display}."


def _compose_closing(
    plan: CoverLetterPlan,
    company: str,
    role: str,
    *,
    employer: dict[str, str],
) -> str:
    """Confident close that invites curiosity about tangible artefacts."""
    del company, role
    if plan.closing_strategy.approach == "contribution_focus":
        return (
            f"I would welcome a conversation about {employer['contribution_role']}. "
            "Happy to open the portfolio, walk through architecture decisions "
            "and engineering trade-offs, and show live demonstrations of the systems "
            "above."
        )
    return (
        f"I would welcome a conversation about {employer['closing_role']}. "
        "If useful, we can inspect the working software together, including "
        "architecture choices, evaluation approach, and the trade-offs I made "
        "along the way."
    )


def _portfolio_lead(contact: dict[str, str] | None, *, count: int = 2) -> str:
    display = _portfolio_display(contact)
    label = "One project" if count == 1 else "Two projects"
    if display:
        return (
            f"{label} from my portfolio ({display}) "
            "is especially useful evidence for this role."
            if count == 1
            else (
                f"{label} from my portfolio ({display}) are especially useful "
                "evidence for this role."
            )
        )
    if count == 1:
        return "One project from my portfolio is especially useful evidence for this role."
    return (
        "Two projects from my portfolio are especially useful evidence for this role."
    )


def _portfolio_display(contact: dict[str, str] | None) -> str | None:
    if not contact:
        return None
    url = (contact.get("portfolio_url") or "").strip()
    if not url:
        return None
    display = url
    for prefix in ("https://", "http://"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break
    return display.rstrip("/")


def _jd_mentions_stakeholders(plan: CoverLetterPlan) -> bool:
    chunks: list[str] = [
        plan.company_alignment.alignment_hook,
        plan.role_motivation.motivation,
    ]
    job = plan.job_analysis
    if job.posting.raw_text:
        chunks.append(job.posting.raw_text[:2000])
    for responsibility in job.responsibilities:
        chunks.append(responsibility.description)
    text = " ".join(chunks).casefold()
    return any(cue in text for cue in _STAKEHOLDER_CUES)


def _credibility_claim_short(profile: CareerProfile) -> str:
    summary = (profile.identity.summary or "").strip()
    lowered = summary.casefold()
    if "3.5 years" in lowered and "data engineering" in lowered:
        return (
            "I am an AI Engineer with 3.5 years of commercial enterprise Data "
            "Engineering experience and an independent AI Engineering practice"
        )
    if summary:
        first = summary.split(".")[0].strip()
        if first.casefold().startswith("ai engineer"):
            return f"I am an {first}"
        return first
    return f"I am an {profile.identity.target_role}"


def _independent_portfolio_years(profile: CareerProfile) -> str:
    """Derive a truthful portfolio-timescale phrase from profile experience dates."""
    summary = (profile.identity.summary or "").casefold()
    if "over the past year" in summary or "past year" in summary:
        return "year"
    if "two years" in summary or "2 years" in summary:
        return "two years"
    if "three years" in summary or "3 years" in summary:
        return "three years"

    months = _portfolio_span_months(profile)
    if months is None:
        return "year"
    if months < 18:
        return "year"
    if months < 30:
        return "two years"
    return "three years"


def _portfolio_span_months(profile: CareerProfile) -> int | None:
    """Months from earliest AI/independent portfolio experience start to now."""
    from datetime import date

    starts: list[date] = []
    for experience in profile.experience:
        kind = (experience.kind or "").casefold()
        title = (experience.title or "").casefold()
        org = (experience.organisation or "").casefold()
        # AI portfolio timescale only — exclude earlier Data Engineering study.
        if kind == "independent_engineering":
            relevant = True
        elif kind == "professional_development" and (
            "ai engineering" in title or "ai engineering" in org
        ):
            relevant = True
        elif "ai engineering" in title and "data engineering" not in title:
            relevant = True
        else:
            relevant = False
        if not relevant or experience.start_date is None:
            continue
        parsed = _coerce_year_month(experience.start_date)
        if parsed is not None:
            starts.append(parsed)
    if not starts:
        return None
    earliest = min(starts)
    today = date.today()
    return max(0, (today.year - earliest.year) * 12 + (today.month - earliest.month))


def _coerce_year_month(value: object) -> date | None:
    from datetime import date

    if isinstance(value, date):
        return date(value.year, value.month, 1)
    text = str(value).strip()
    match = re.match(r"^(\d{4})-(\d{2})", text)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return date(year, month, 1)


def _is_weak_attraction(text: str) -> bool:
    if not text or len(text) < 28:
        return True
    folded = text.casefold()
    if any(fluff in folded for fluff in _MARKETING_FLUFF):
        return True
    weak_only = (
        "ai engineering work",
        "production-minded ai engineering delivery",
        "ai engineer",
    )
    return folded in weak_only


def _scrub_marketing(text: str) -> str:
    cleaned = text
    for fluff in _MARKETING_FLUFF:
        cleaned = re.sub(re.escape(fluff), "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,;.-")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(
        r"\bAI systems\s+fintech\b",
        "AI systems for fintech",
        cleaned,
        flags=re.I,
    )
    return cleaned


def _themes_overlap(attraction: str, themes: str) -> bool:
    left = attraction.casefold()
    right = themes.casefold()
    if left == right or right in left or left in right:
        return True
    left_tokens = {token for token in re.findall(r"[a-z0-9]+", left) if len(token) > 3}
    right_tokens = {token for token in re.findall(r"[a-z0-9]+", right) if len(token) > 3}
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.6


def _clean_phrase(text: str) -> str:
    cleaned = " ".join(text.split()).strip().rstrip(".")
    cleaned = cleaned.rstrip("…").rstrip()
    return cleaned


def _as_chance_clause(phrase: str, *, limit: int = 120) -> str:
    cleaned = _truncate_words(_scrub_marketing(_clean_phrase(phrase)), limit=limit)
    including_at = cleaned.casefold().find(", including")
    if including_at > 40:
        cleaned = cleaned[:including_at].rstrip()
    if not cleaned or _is_recruiting_noun_phrase(cleaned):
        return "build production AI systems with clear engineering accountability"
    infinitive = _to_infinitive_verb_list(cleaned)
    first = re.split(r"[,\s]+", infinitive, maxsplit=1)[0].casefold() if infinitive else ""
    if first in _IMPERATIVE_TO_GERUND or first in {"learn", "help", "work"}:
        return infinitive
    # Do not wrap noun phrases ("an experienced AI Engineer…") as "contribute to …".
    if _is_recruiting_noun_phrase(infinitive) or first in {
        "a",
        "an",
        "the",
        "exciting",
        "opportunity",
        "experienced",
        "skilled",
        "senior",
        "junior",
    }:
        return "build production AI systems with clear engineering accountability"
    return f"contribute to {infinitive}"


def _is_recruiting_noun_phrase(text: str) -> bool:
    folded = text.casefold().strip()
    if not folded:
        return True
    if any(
        marker in folded
        for marker in (
            "has become available",
            "exciting opportunity",
            "opportunity has become",
            "to join a",
            "to join an",
        )
    ):
        return True
    return bool(
        re.match(
            r"^(?:a|an|the)\s+(?:experienced|skilled|senior|junior|passionate)\b",
            folded,
        )
    )


def _as_gerund_phrase(phrase: str, *, limit: int = 100) -> str:
    cleaned = _truncate_words(_scrub_marketing(_clean_phrase(phrase)), limit=limit)
    including_at = cleaned.casefold().find(", including")
    if including_at > 40:
        cleaned = cleaned[:including_at].rstrip()
    including_at = cleaned.casefold().find(" including ")
    if including_at > 40:
        cleaned = cleaned[:including_at].rstrip()
    if not cleaned:
        return "production AI Engineering delivery"
    return _to_gerund_verb_list(cleaned)


def _to_infinitive_verb_list(phrase: str) -> str:
    return _rewrite_leading_verb_list(phrase, gerund=False)


def _to_gerund_verb_list(phrase: str) -> str:
    return _rewrite_leading_verb_list(phrase, gerund=True)


def _rewrite_leading_verb_list(phrase: str, *, gerund: bool) -> str:
    match = re.match(
        r"^([A-Za-z]+)((?:,\s*[A-Za-z]+)*)(?:\s+and\s+([A-Za-z]+))?(?:\s+|$)(.*)$",
        phrase.strip(),
        flags=re.DOTALL,
    )
    if not match:
        return _lowercase_leading(phrase)

    def convert(word: str) -> str:
        key = word.casefold()
        base = _THIRD_PERSON_TO_BASE.get(key, key)
        if gerund:
            return _IMPERATIVE_TO_GERUND.get(
                base, base if base.endswith("ing") else f"{base}ing"
            )
        # Already-gerund leads ("Designing and building…") → imperative base.
        if base.endswith("ing"):
            for imperative, gerund_form in _IMPERATIVE_TO_GERUND.items():
                if gerund_form == base:
                    return imperative
        return base

    first = convert(match.group(1))
    middle = match.group(2) or ""

    def convert_middle(found: re.Match[str]) -> str:
        return f"{found.group(1)}{convert(found.group(2))}"

    middle = re.sub(r"(,\s*)([A-Za-z]+)", convert_middle, middle)
    and_verb = match.group(3)
    rest = (match.group(4) or "").strip()
    if and_verb:
        body = f"{first}{middle} and {convert(and_verb)}"
    else:
        body = f"{first}{middle}"
    return f"{body} {rest}".strip() if rest else body.strip()


def _lowercase_leading(text: str) -> str:
    if not text:
        return text
    first = text.split()[0]
    if first.isupper() and len(first) <= 4:
        return text
    if text[0].isupper():
        return text[0].lower() + text[1:]
    return text


def _truncate_words(text: str, *, limit: int) -> str:
    if len(text) <= limit:
        cleaned = text
    else:
        cleaned = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") or text[:limit]
    while True:
        lowered = cleaned.casefold()
        stripped = False
        for suffix in (
            " and",
            " or",
            " including the",
            " including",
            " with",
            " for",
            " to",
            " the",
            " a",
            " an",
        ):
            if lowered.endswith(suffix):
                cleaned = cleaned[: -len(suffix)].rstrip(",;: ")
                stripped = True
                break
        if not stripped:
            break
    return cleaned


def _strip_ai_punctuation(text: str) -> str:
    """Replace em/en dashes without leaving orphaned sentence fragments."""
    cleaned = text.replace("—", "; ").replace("–", ", ")
    cleaned = re.sub(r";\s*;", ";", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _letter_quality_ok(
    paragraphs: list[str],
    *,
    employer: dict[str, str],
) -> bool:
    """Deterministic quality gate: incomplete sentences, bad openings, recruiter slips."""
    joined = " ".join(paragraphs)
    folded = joined.casefold()
    if "contribute to an experienced" in folded:
        return False
    if "contribute to an exciting opportunity" in folded:
        return False
    if "has become available" in folded:
        return False
    dangling = (
        " in.",
        " for.",
        " to.",
        " and.",
        " with.",
        " the.",
        " a.",
        " an.",
        " of.",
    )
    for paragraph in paragraphs:
        stripped = paragraph.rstrip()
        lowered = stripped.casefold()
        if any(lowered.endswith(suffix.strip()) for suffix in dangling):
            return False
        # Incomplete truncated clause before the period.
        if re.search(r"\b(?:in|for|to|and|with|the|a|an|of)\.\s*$", stripped):
            return False
    # Recruiter ads must not imply the agency owns the engineering environment.
    if employer.get("mode") == "recruiter":
        if re.search(r"recruitment'?s\s+technical challenges", folded):
            return False
        if "advertised through" not in folded and "your client" not in folded:
            return False
    # Repeated phrase density for common filler.
    for phrase in (
        "traceable, reviewable",
        "evidence-backed and reviewable",
    ):
        if folded.count(phrase) >= 3:
            return False
    return True


def _fallback_paragraphs(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None,
) -> list[str]:
    employer = _employer_voice(plan)
    chance = "build production AI systems with clear engineering accountability"
    paragraphs = [
        (
            f"Recent production-style AI engineering work is a strong fit for "
            f"{employer['opening_subject']}. I want to {chance}."
        ),
        (
            f"{_credibility_claim_short(profile)}. Over the past "
            f"{_independent_portfolio_years(profile)} I have built a portfolio of "
            "production-style AI engineering projects. I build explainable, "
            f"reviewable AI systems and would bring that approach to "
            f"{employer['challenge_owner']}."
        ),
    ]
    projects = _compose_projects(plan, profile, contact=contact)
    if projects:
        paragraphs.append(_strip_ai_punctuation(projects))
    paragraphs.append(
        f"I would welcome a conversation about {employer['closing_role']}. "
        "I can share working software and live demonstrations from the portfolio."
    )
    return [
        _strip_ai_punctuation(_clamp_sentence_spacing(part)) for part in paragraphs
    ]


def _clamp_sentence_spacing(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    return cleaned
