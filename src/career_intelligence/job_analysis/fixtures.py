"""Representative Australian job-description fixtures for deterministic extraction.

These texts are deliberately compact. They exist so the service architecture can run
without network access — not as a substitute for real LLM extraction.

Builders return untrusted payload mappings (no ``posting`` field). The service binds
the caller-supplied JobPosting after extraction.
"""

from __future__ import annotations

from collections.abc import Callable

from .extractor import JobAnalysisPayload
from .models import JobPosting

PayloadBuilder = Callable[[], JobAnalysisPayload]

# Distinctive markers used by FixtureExtractor for deterministic matching.
MARKER_AI_ENGINEER = "[CIC-FIXTURE:ai-engineer]"
MARKER_APPLIED_AI = "[CIC-FIXTURE:applied-ai-engineer]"
MARKER_DATA_ENGINEER = "[CIC-FIXTURE:data-engineer]"
MARKER_AI_SOLUTIONS = "[CIC-FIXTURE:ai-solutions-engineer]"
MARKER_AMBIGUOUS_SENIORITY = "[CIC-FIXTURE:ambiguous-seniority]"
MARKER_MISSING_SALARY = "[CIC-FIXTURE:missing-salary]"
MARKER_REMOTE = "[CIC-FIXTURE:remote]"
MARKER_CONTRACT = "[CIC-FIXTURE:contract]"
MARKER_NO_TECHNOLOGIES = "[CIC-FIXTURE:no-technologies]"
MARKER_WORKING_RIGHTS = "[CIC-FIXTURE:working-rights]"


def _ev(excerpt: str, section: str | None = None) -> dict[str, str]:
    payload: dict[str, str] = {"excerpt": excerpt}
    if section is not None:
        payload["section"] = section
    return payload


def posting_ai_engineer() -> JobPosting:
    return JobPosting(
        title="Senior AI Engineer",
        company="Northside Analytics",
        raw_text=f"""
{MARKER_AI_ENGINEER}
Senior AI Engineer — Northside Analytics (Melbourne)

About the role
We are hiring a Senior AI Engineer to design and ship production LLM applications for
Australian enterprise clients. You will own retrieval pipelines, evaluation harnesses,
and safe deployment patterns.

Responsibilities
• Build and maintain LLM applications using Python and LangChain
• Partner with data engineers on feature pipelines and model observability
• Mentor engineers on prompt evaluation and production readiness

Requirements
• 5+ years software engineering experience required
• Strong Python required; LangChain experience preferred
• Production LLM or RAG experience required

Location & employment
Hybrid Melbourne — 3 days in the CBD office. Full-time permanent.
Salary $150,000–$180,000 AUD + super.
""".strip(),
    )


def posting_applied_ai_engineer() -> JobPosting:
    return JobPosting(
        title="Applied AI Engineer",
        company="Harbour Labs",
        raw_text=f"""
{MARKER_APPLIED_AI}
Applied AI Engineer — Harbour Labs (Sydney)

Join our applied AI team to prototype and productise customer-facing assistants.
You will work closely with solution architects and customer success.

Responsibilities
• Deliver applied AI prototypes into production services
• Fine-tune and evaluate models for customer use cases
• Document patterns for reuse across engagements

Requirements
• 3+ years building ML or AI-powered products required
• Python and FastAPI required; Azure OpenAI preferred
• Stakeholder-facing delivery experience preferred

Location & employment
Hybrid Sydney (Barangaroo), 2 days in office. Full-time permanent.
Salary $140,000–$165,000 AUD.
""".strip(),
    )


def posting_data_engineer() -> JobPosting:
    return JobPosting(
        title="Data Engineer",
        company="Southern Grid Energy",
        raw_text=f"""
{MARKER_DATA_ENGINEER}
Data Engineer — Southern Grid Energy (Melbourne)

We need a Data Engineer to build reliable analytics platforms on modern lakehouse tooling.

Responsibilities
• Design and operate batch and streaming pipelines
• Model curated datasets for analytics and AI consumers
• Improve data quality and observability

Requirements
• 4+ years data engineering experience required
• Python and SQL required; Spark and dbt preferred
• Cloud warehouse experience (Snowflake or Databricks) required

Location & employment
Hybrid Melbourne. Full-time permanent.
Salary $130,000–$155,000 AUD + super.
""".strip(),
    )


def posting_ai_solutions_engineer() -> JobPosting:
    return JobPosting(
        title="AI Solutions Engineer",
        company="Pacific Cloud AI",
        raw_text=f"""
{MARKER_AI_SOLUTIONS}
AI Solutions Engineer — Pacific Cloud AI (Brisbane)

Help enterprise customers adopt our AI platform. Blend technical depth with customer
discovery and solution design.

Responsibilities
• Lead discovery workshops and translate requirements into AI solution designs
• Build reference implementations with customers
• Support RFPs and proof-of-value engagements

Requirements
• 4+ years solutions engineering or consulting required
• Python required; LLM APIs preferred
• Strong communication with technical and commercial stakeholders required

Location & employment
Hybrid Brisbane CBD. Full-time permanent.
Salary $145,000–$170,000 AUD.
""".strip(),
    )


def posting_ambiguous_seniority() -> JobPosting:
    return JobPosting(
        title="Senior / Lead AI Engineer",
        company="Indigo Systems",
        raw_text=f"""
{MARKER_AMBIGUOUS_SENIORITY}
Senior / Lead AI Engineer — Indigo Systems (Melbourne)

We are open to Senior or Lead level depending on experience.

Responsibilities
• Own LLM application delivery end-to-end
• Optionally lead a small pod of engineers
• Reports to the Head of Engineering

Requirements
• Senior engineers with deep hands-on delivery, or Lead candidates who still code
• Python and production LLM experience required

Location & employment
Hybrid Melbourne, 3 days in office. Full-time permanent.
Salary $160,000–$195,000 AUD.
""".strip(),
    )


def posting_missing_salary() -> JobPosting:
    return JobPosting(
        title="AI Engineer",
        company="Quiet Harbour Digital",
        raw_text=f"""
{MARKER_MISSING_SALARY}
AI Engineer — Quiet Harbour Digital (Melbourne)

Build internal AI tooling for operations teams.

Responsibilities
• Develop RAG assistants over internal knowledge bases
• Integrate models into existing Python services

Requirements
• Python required; LangChain preferred
• 2+ years software engineering required

Location & employment
Hybrid Melbourne. Full-time permanent.
Competitive salary package — details discussed at interview.
""".strip(),
    )


def posting_remote() -> JobPosting:
    return JobPosting(
        title="AI Engineer",
        company="Coastal Ops AI",
        raw_text=f"""
{MARKER_REMOTE}
AI Engineer — Coastal Ops AI (Remote Australia)

Fully remote within Australia. Help us ship operational copilots for field teams.

Responsibilities
• Build LLM workflows for triage and summarisation
• Maintain evaluation suites and safety checks

Requirements
• Python required; AWS experience preferred
• Production AI systems experience required

Location & employment
Fully remote within Australia. Full-time permanent.
Salary $145,000–$170,000 AUD.
""".strip(),
    )


def posting_no_technologies() -> JobPosting:
    """Outcome-focused AI role with no named technology stack."""
    return JobPosting(
        title="AI Engineer",
        company="Sparse Spec AI",
        raw_text=f"""
{MARKER_NO_TECHNOLOGIES}
AI Engineer — Sparse Spec AI (Remote Australia)

Outcome-focused role building internal AI assistants for operations teams.

Responsibilities
• Improve operational workflows with AI-assisted tooling
• Collaborate with business stakeholders on adoption

Requirements
• Demonstrated ability to deliver AI solutions in production environments
• Strong communication skills

Location & employment
Fully remote within Australia. Full-time permanent.
Salary $145,000–$170,000 AUD.
""".strip(),
    )


def posting_working_rights() -> JobPosting:
    """AI role stating Australian working-rights without candidate eligibility evidence."""
    return JobPosting(
        title="AI Engineer",
        company="National Systems Group",
        raw_text=f"""
{MARKER_WORKING_RIGHTS}
AI Engineer — National Systems Group (Melbourne)

Build internal AI tooling for enterprise clients.

Requirements
• Must have unrestricted Australian working rights
• Experience delivering AI solutions

Location & employment
Hybrid Melbourne. Full-time permanent.
""".strip(),
    )


def posting_contract() -> JobPosting:
    return JobPosting(
        title="Contract AI Engineer",
        company="Redfern Delivery Partners",
        raw_text=f"""
{MARKER_CONTRACT}
Contract AI Engineer — Redfern Delivery Partners (Sydney)

6-month full-time contract to accelerate an enterprise RAG rollout.

Responsibilities
• Implement retrieval pipelines and evaluation tooling
• Hand over runbooks to the permanent engineering team

Requirements
• Immediate start preferred
• Python and LangChain required
• Prior contract delivery in regulated environments preferred

Location & employment
Hybrid Sydney, 3 days on-site. Full-time contract (initial 6 months).
Rate $850–$950 per day + GST.
""".strip(),
    )


def analysis_for_ai_engineer() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("Senior AI Engineer", "title")],
        },
        "seniority": {
            "level": "senior",
            "ambiguous": False,
            "evidence": [_ev("Senior AI Engineer", "title")],
        },
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Strong Python required", "requirements")],
            },
            {
                "name": "LangChain",
                "level": "preferred",
                "evidence": [_ev("LangChain experience preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": (
                    "Build and maintain LLM applications using Python and LangChain"
                ),
                "evidence": [
                    _ev(
                        "Build and maintain LLM applications using Python and LangChain",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 150_000,
            "maximum": 180_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $150,000–$180,000 AUD + super",
            "evidence": [_ev("Salary $150,000–$180,000 AUD + super", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "details": "3 days in the CBD office",
            "evidence": [_ev("Hybrid Melbourne — 3 days in the CBD office", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "5+ years software engineering experience",
                "level": "required",
                "minimum_years": 5,
                "evidence": [
                    _ev(
                        "5+ years software engineering experience required",
                        "requirements",
                    )
                ],
            },
            {
                "description": "Production LLM or RAG experience",
                "level": "required",
                "evidence": [
                    _ev("Production LLM or RAG experience required", "requirements")
                ],
            },
        ],
    }


def analysis_for_applied_ai() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("Applied AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python and FastAPI required", "requirements")],
            },
            {
                "name": "FastAPI",
                "level": "required",
                "evidence": [_ev("Python and FastAPI required", "requirements")],
            },
            {
                "name": "Azure OpenAI",
                "level": "preferred",
                "evidence": [_ev("Azure OpenAI preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": "Deliver applied AI prototypes into production services",
                "evidence": [
                    _ev(
                        "Deliver applied AI prototypes into production services",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 140_000,
            "maximum": 165_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $140,000–$165,000 AUD",
            "evidence": [_ev("Salary $140,000–$165,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Sydney",
            "evidence": [_ev("Hybrid Sydney (Barangaroo)", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "details": "2 days in office",
            "evidence": [_ev("Hybrid Sydney (Barangaroo), 2 days in office", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "3+ years building ML or AI-powered products",
                "level": "required",
                "minimum_years": 3,
                "evidence": [
                    _ev(
                        "3+ years building ML or AI-powered products required",
                        "requirements",
                    )
                ],
            },
            {
                "description": "Stakeholder-facing delivery experience",
                "level": "preferred",
                "evidence": [
                    _ev(
                        "Stakeholder-facing delivery experience preferred",
                        "requirements",
                    )
                ],
            },
        ],
    }


def analysis_for_data_engineer() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "data_engineering",
            "evidence": [_ev("Data Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python and SQL required", "requirements")],
            },
            {
                "name": "SQL",
                "level": "required",
                "evidence": [_ev("Python and SQL required", "requirements")],
            },
            {
                "name": "Spark",
                "level": "preferred",
                "evidence": [_ev("Spark and dbt preferred", "requirements")],
            },
            {
                "name": "dbt",
                "level": "preferred",
                "evidence": [_ev("Spark and dbt preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": "Design and operate batch and streaming pipelines",
                "evidence": [
                    _ev(
                        "Design and operate batch and streaming pipelines",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 130_000,
            "maximum": 155_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $130,000–$155,000 AUD + super",
            "evidence": [_ev("Salary $130,000–$155,000 AUD + super", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "4+ years data engineering experience",
                "level": "required",
                "minimum_years": 4,
                "evidence": [
                    _ev("4+ years data engineering experience required", "requirements")
                ],
            }
        ],
    }


def analysis_for_ai_solutions() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_solutions",
            "evidence": [_ev("AI Solutions Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python required", "requirements")],
            },
            {
                "name": "LLM APIs",
                "level": "preferred",
                "evidence": [_ev("LLM APIs preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": (
                    "Lead discovery workshops and translate requirements into AI "
                    "solution designs"
                ),
                "evidence": [
                    _ev(
                        "Lead discovery workshops and translate requirements into AI "
                        "solution designs",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 145_000,
            "maximum": 170_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $145,000–$170,000 AUD",
            "evidence": [_ev("Salary $145,000–$170,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Brisbane",
            "evidence": [_ev("Hybrid Brisbane CBD", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [_ev("Hybrid Brisbane CBD", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "4+ years solutions engineering or consulting",
                "level": "required",
                "minimum_years": 4,
                "evidence": [
                    _ev(
                        "4+ years solutions engineering or consulting required",
                        "requirements",
                    )
                ],
            }
        ],
    }


def analysis_for_ambiguous_seniority() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("Senior / Lead AI Engineer", "title")],
        },
        "seniority": {
            "level": "unknown",
            "ambiguous": True,
            "candidate_levels": ["senior", "lead"],
            "evidence": [
                _ev("Senior / Lead AI Engineer", "title"),
                _ev("open to Senior or Lead level depending on experience", "about"),
            ],
        },
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [
                    _ev("Python and production LLM experience required", "requirements")
                ],
            }
        ],
        "responsibilities": [
            {
                "description": "Own LLM application delivery end-to-end",
                "evidence": [
                    _ev("Own LLM application delivery end-to-end", "responsibilities")
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 160_000,
            "maximum": 195_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $160,000–$195,000 AUD",
            "evidence": [_ev("Salary $160,000–$195,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_ev("Hybrid Melbourne, 3 days in office", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "details": "3 days in office",
            "evidence": [_ev("Hybrid Melbourne, 3 days in office", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "Python and production LLM experience",
                "level": "required",
                "evidence": [
                    _ev("Python and production LLM experience required", "requirements")
                ],
            }
        ],
    }


def analysis_for_missing_salary() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python required", "requirements")],
            },
            {
                "name": "LangChain",
                "level": "preferred",
                "evidence": [_ev("LangChain preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": "Develop RAG assistants over internal knowledge bases",
                "evidence": [
                    _ev(
                        "Develop RAG assistants over internal knowledge bases",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {"clarity": "unstated"},
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "2+ years software engineering",
                "level": "required",
                "minimum_years": 2,
                "evidence": [_ev("2+ years software engineering required", "requirements")],
            }
        ],
    }


def analysis_for_remote() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python required", "requirements")],
            },
            {
                "name": "AWS",
                "level": "preferred",
                "evidence": [_ev("AWS experience preferred", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": "Build LLM workflows for triage and summarisation",
                "evidence": [
                    _ev(
                        "Build LLM workflows for triage and summarisation",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 145_000,
            "maximum": 170_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $145,000–$170,000 AUD",
            "evidence": [_ev("Salary $145,000–$170,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Remote Australia",
            "evidence": [_ev("Fully remote within Australia", "location")],
        },
        "work_arrangement": {
            "arrangement": "remote",
            "details": "remote within Australia only",
            "evidence": [_ev("Fully remote within Australia", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "Production AI systems experience",
                "level": "required",
                "evidence": [
                    _ev("Production AI systems experience required", "requirements")
                ],
            }
        ],
    }


def analysis_for_contract() -> JobAnalysisPayload:
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("Contract AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [
            {
                "name": "Python",
                "level": "required",
                "evidence": [_ev("Python and LangChain required", "requirements")],
            },
            {
                "name": "LangChain",
                "level": "required",
                "evidence": [_ev("Python and LangChain required", "requirements")],
            },
        ],
        "responsibilities": [
            {
                "description": "Implement retrieval pipelines and evaluation tooling",
                "evidence": [
                    _ev(
                        "Implement retrieval pipelines and evaluation tooling",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 850,
            "maximum": 950,
            "currency": "AUD",
            "period": "day",
            "raw_text": "Rate $850–$950 per day + GST",
            "evidence": [_ev("Rate $850–$950 per day + GST", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Sydney",
            "evidence": [_ev("Hybrid Sydney, 3 days on-site", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "details": "3 days on-site",
            "evidence": [_ev("Hybrid Sydney, 3 days on-site", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "contract",
            "evidence": [_ev("Full-time contract (initial 6 months)", "employment")],
        },
        "experience_requirements": [
            {
                "description": "Prior contract delivery in regulated environments",
                "level": "preferred",
                "evidence": [
                    _ev(
                        "Prior contract delivery in regulated environments preferred",
                        "requirements",
                    )
                ],
            }
        ],
    }


def analysis_for_no_technologies() -> JobAnalysisPayload:
    """Sparse AI advert — no named technologies; experience requirements only."""
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [],
        "responsibilities": [
            {
                "description": "Improve operational workflows with AI-assisted tooling",
                "evidence": [
                    _ev(
                        "Improve operational workflows with AI-assisted tooling",
                        "responsibilities",
                    )
                ],
            }
        ],
        "compensation": {
            "clarity": "stated",
            "minimum": 145_000,
            "maximum": 170_000,
            "currency": "AUD",
            "period": "year",
            "raw_text": "Salary $145,000–$170,000 AUD",
            "evidence": [_ev("Salary $145,000–$170,000 AUD", "compensation")],
        },
        "location": {
            "clarity": "stated",
            "summary": "Remote Australia",
            "evidence": [_ev("Fully remote within Australia", "location")],
        },
        "work_arrangement": {
            "arrangement": "remote",
            "details": "remote within Australia only",
            "evidence": [_ev("Fully remote within Australia", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": (
                    "Demonstrated ability to deliver AI solutions in production environments"
                ),
                "level": "required",
                "evidence": [
                    _ev(
                        "Demonstrated ability to deliver AI solutions in production environments",
                        "requirements",
                    )
                ],
            }
        ],
    }


def analysis_for_working_rights() -> JobAnalysisPayload:
    """Working-rights requirement present; no technology stack named."""
    return {
        "role_family": {
            "family": "ai_engineering",
            "evidence": [_ev("AI Engineer", "title")],
        },
        "seniority": {"level": "unknown", "ambiguous": False},
        "technologies": [],
        "responsibilities": [],
        "compensation": {"clarity": "unstated"},
        "location": {
            "clarity": "stated",
            "summary": "Melbourne",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "work_arrangement": {
            "arrangement": "hybrid",
            "evidence": [_ev("Hybrid Melbourne", "location")],
        },
        "employment": {
            "working_hours": "full_time",
            "engagement_type": "permanent",
            "evidence": [_ev("Full-time permanent", "employment")],
        },
        "experience_requirements": [
            {
                "description": "Unrestricted Australian working rights",
                "level": "required",
                "evidence": [
                    _ev(
                        "Must have unrestricted Australian working rights",
                        "requirements",
                    )
                ],
            }
        ],
    }


FIXTURE_BUILDERS: dict[str, PayloadBuilder] = {
    MARKER_AI_ENGINEER: analysis_for_ai_engineer,
    MARKER_APPLIED_AI: analysis_for_applied_ai,
    MARKER_DATA_ENGINEER: analysis_for_data_engineer,
    MARKER_AI_SOLUTIONS: analysis_for_ai_solutions,
    MARKER_AMBIGUOUS_SENIORITY: analysis_for_ambiguous_seniority,
    MARKER_MISSING_SALARY: analysis_for_missing_salary,
    MARKER_REMOTE: analysis_for_remote,
    MARKER_CONTRACT: analysis_for_contract,
    MARKER_NO_TECHNOLOGIES: analysis_for_no_technologies,
    MARKER_WORKING_RIGHTS: analysis_for_working_rights,
}

REPRESENTATIVE_POSTINGS = {
    "ai_engineer": posting_ai_engineer,
    "applied_ai_engineer": posting_applied_ai_engineer,
    "data_engineer": posting_data_engineer,
    "ai_solutions_engineer": posting_ai_solutions_engineer,
    "ambiguous_seniority": posting_ambiguous_seniority,
    "missing_salary": posting_missing_salary,
    "remote": posting_remote,
    "contract": posting_contract,
    "no_technologies": posting_no_technologies,
    "working_rights": posting_working_rights,
}
