"""Deterministic cover letter prose composition from an approved plan.

The planner selects evidence; this module writes human letter prose.
Planner vocabulary must never appear in the finished document.
"""

from __future__ import annotations

import re

from career_intelligence.profile.models import CareerProfile, Project

from .models import CoverLetterPlan, StrongestProject
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

    opening = _compose_opening(plan, company, role)
    motivation = _compose_motivation(plan, profile, company)
    project_paragraphs = _compose_project_paragraphs(plan, profile, contact=contact)
    closing = _compose_closing(plan, company, role)

    paragraphs = [opening, motivation, *project_paragraphs, closing]
    # Keep within CoverLetter schema (max 5): merge trailing projects if needed.
    if len(paragraphs) > 5:
        head = paragraphs[:2]
        projects = paragraphs[2:-1]
        closing_part = paragraphs[-1]
        merged_projects = " ".join(projects)
        paragraphs = [*head, merged_projects, closing_part]

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
    return validated


def _possessive(name: str) -> str:
    cleaned = name.strip()
    if cleaned.casefold().endswith("s"):
        return f"{cleaned}'"
    return f"{cleaned}'s"


def _compose_opening(plan: CoverLetterPlan, company: str, role: str) -> str:
    """Specific attraction to this role's engineering work."""
    attraction = _scrub_marketing(_clean_phrase(plan.company_alignment.alignment_hook))
    themes = _scrub_marketing(_clean_phrase(plan.role_motivation.motivation))

    primary = attraction
    secondary = themes
    if _is_weak_attraction(primary) and secondary:
        primary, secondary = secondary, attraction

    chance = _as_chance_clause(primary)
    opening = (
        f"What drew me to {_possessive(company)} {role} role is the chance to "
        f"{chance}."
    )

    if not secondary or _themes_overlap(primary, secondary) or _is_weak_attraction(secondary):
        return (
            f"{opening} That kind of production engineering, with clear "
            "accountability, is the work I want to do next."
        )

    interest = _as_gerund_phrase(secondary, limit=100)
    return (
        f"{opening} I am particularly interested in {interest}, where careful "
        "design and reviewable results matter."
    )


def _compose_motivation(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    company: str,
) -> str:
    """Credibility, portfolio breadth, philosophy, and collaboration."""
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
        "I enjoy collaborating with engineers, learning from experienced teammates "
        "and sharing knowledge as we build AI solutions together."
    )
    stakeholder = ""
    if _jd_mentions_stakeholders(plan):
        stakeholder = (
            " I am also comfortable translating business requirements into "
            "practical AI systems and supporting adoption with clear communication."
        )
    return (
        f"{_credibility_claim_short(profile)}. {breadth} {craft} "
        f"{collaboration}{stakeholder} "
        f"That is the approach I would bring to {_possessive(company)} "
        "technical challenges."
    )


def _compose_project_paragraphs(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None,
) -> list[str]:
    """One short paragraph per selected project, with varied phrasing."""
    projects = list(plan.strongest_projects[:3])
    if not projects:
        return []

    portfolio_lead = _portfolio_lead(contact, count=len(projects))
    by_id = {project.id: project for project in profile.projects}
    paragraphs: list[str] = []
    for index, project in enumerate(projects):
        block = _project_block(project, by_id.get(project.project_id), variant=index)
        if index == 0:
            paragraphs.append(f"{portfolio_lead} {block}")
        else:
            paragraphs.append(block)
    return paragraphs


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
    variant: int,
) -> str:
    """What it does, why it matters, and why it is relevant (varied voice)."""
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

    style = variant % 3
    if style == 0:
        return (
            f"{name} {does}. "
            f"The engineering centre of it is {engineering}. "
            f"In practice, {outcome}."
        )
    if style == 1:
        return (
            f"Another strong example is {name}, which {does}. "
            f"What I would highlight in an interview is {engineering}. "
            f"In practice, {outcome}."
        )
    return (
        f"I would also point to {name}. It {does}. "
        f"Under the hood that means {engineering}. "
        f"If helpful, I can walk through the working software and the trade-offs "
        "behind it."
    )


def _compose_closing(plan: CoverLetterPlan, company: str, role: str) -> str:
    """Confident close that invites curiosity about tangible artefacts."""
    if plan.closing_strategy.approach == "contribution_focus":
        return (
            f"I would welcome a conversation about {_possessive(company)} {role} "
            "work. Happy to open the portfolio, walk through architecture decisions "
            "and engineering trade-offs, and show live demonstrations of the systems "
            "above."
        )
    return (
        f"I would welcome a conversation about the {role} role at {company}. "
        "If useful, we can look at the working software together, including "
        "architecture choices and the trade-offs I made along the way."
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
    summary = (profile.identity.summary or "").casefold()
    if "two years" in summary or "2 years" in summary:
        return "two years"
    del profile
    return "two years"


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
    if not cleaned:
        return "build production AI systems with clear engineering accountability"
    infinitive = _to_infinitive_verb_list(cleaned)
    first = re.split(r"[,\s]+", infinitive, maxsplit=1)[0].casefold() if infinitive else ""
    if first in _IMPERATIVE_TO_GERUND or first in {"learn", "help", "work"}:
        return infinitive
    return f"contribute to {infinitive}"


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
    """Prefer commas and full stops over em/en dashes."""
    cleaned = text.replace("—", ". ").replace("–", ", ")
    cleaned = re.sub(r"\.\s*\.", ".", cleaned)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r",\s*,", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def _fallback_paragraphs(
    plan: CoverLetterPlan,
    profile: CareerProfile,
    *,
    contact: dict[str, str] | None,
) -> list[str]:
    company = plan.company_alignment.company
    role = plan.role_motivation.role_title
    chance = _as_chance_clause(
        _scrub_marketing(plan.company_alignment.alignment_hook)
    )
    paragraphs = [
        (
            f"What drew me to {_possessive(company)} {role} role is the chance to "
            f"{chance}."
        ),
        (
            f"{_credibility_claim_short(profile)}. I build explainable, "
            "reviewable AI systems and enjoy collaborating with engineers."
        ),
    ]
    projects = _compose_projects(plan, profile, contact=contact)
    if projects:
        paragraphs.append(_strip_ai_punctuation(projects))
    paragraphs.append(
        f"I would welcome a conversation about the {role} role at {company}. "
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
