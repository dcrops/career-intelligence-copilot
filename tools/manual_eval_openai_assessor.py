"""Manual live evaluation harness for FR-003 OpenAI opportunity assessment.

Engineering tool only — not a product CLI. Requires OPENAI_API_KEY in the environment.

Pipeline per case:
  JobPosting → JobAnalysisService(OpenAIJobExtractor) → JobAnalysis
  CareerProfileService.load() → CareerProfile
  OpportunityAssessmentService(OpenAIAssessor) → OpportunityAssessment

Usage:
  python tools/manual_eval_openai_assessor.py
  python tools/manual_eval_openai_assessor.py --case applied-ai
  python tools/manual_eval_openai_assessor.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass

import truststore

truststore.inject_into_ssl()

from career_intelligence.job_analysis import JobAnalysisService, JobPosting
from career_intelligence.job_analysis.extraction_prompt import EXTRACTION_PROMPT_VERSION
from career_intelligence.job_analysis.fixtures import (
    posting_ai_engineer,
    posting_applied_ai_engineer,
    posting_contract,
    posting_data_engineer,
    posting_missing_salary,
    posting_no_technologies,
)
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor
from career_intelligence.opportunity_assessment import (
    OpportunityAssessment,
    OpportunityAssessmentError,
    OpportunityAssessmentService,
    OpportunityAssessmentValidationError,
)
from career_intelligence.opportunity_assessment.assessment_prompt import (
    ASSESSMENT_PROMPT_VERSION,
)
from career_intelligence.opportunity_assessment.openai_assessor import OpenAIAssessor
from career_intelligence.profile import CareerProfileService

# LinkedIn AI Engineer — production systems + working rights + on-site (FR-002 eval family).
LINKEDIN_PRODUCTION_AI_JOB_TEXT = """
AI Engineer

Greater Melbourne Area

150K AUD/yr - 180K AUD/yr
On-site
Full-time

About the job
Melbourne based, must have full working rights in Australia

About the Role

Our client is building out its internal AI capability and needs an AI Engineer to turn
redesigned workflows into production grade solutions. This is not a role where you use
AI tools to help you code faster. This is a role where you build the AI systems the
rest of the business relies on every day.

What You'll Do

You'll take redesigned business workflows and turn them into AI systems that actually
run in production, end to end. That spans everything from the underlying models and
orchestration through to the infrastructure they run on and the systems they connect to.

What You'll Bring

This is a hands on role for someone who has genuinely built and shipped AI powered
systems, not someone who has used AI tools to help them ship other things faster.
You'll have several years in software, data, or automation work.

MUST HAVE CURRENT, FULL WORKING RIGHTS IN AUSTRALIA
""".strip()

# SEEK Developer Programmer — broad stack, lower salary (FR-002 eval 4 family).
DEVELOPER_PROGRAMMER_JOB_TEXT = """
Developer Programmer

Melbourne VIC
$85,000 – $90,000 per year
Full-time, Permanent

About the role
Join a stable organisation maintaining and enhancing business applications.

Responsibilities
• Develop and maintain software across the technology stack
• Collaborate with analysts and testers on delivery
• Support production systems and defect resolution

Requirements
• Experience across multiple programming languages and frameworks
• SQL and web development experience
• Ability to work in a team environment
• Strong communication skills

Location & employment
On-site Melbourne. Full-time permanent role.
Salary $85,000–$90,000 AUD per year.
""".strip()

# LinkedIn AI Engineer — outcome-focused, no named technologies (FR-002 eval 5 family).
LINKEDIN_NO_TECH_JOB_TEXT = """
AI Engineer

Melbourne VIC
$140,000 – $165,000 per year
On-site
Full-time

About the role
We are expanding our internal AI capability to deliver production-grade assistants and
workflow automation for enterprise operations teams.

Responsibilities
• Design and deliver AI-assisted workflow improvements
• Partner with business stakeholders on adoption
• Maintain reliable production AI services

Requirements
• Demonstrated ability to deliver AI solutions in production environments
• Strong communication and stakeholder engagement
• Track record building systems end to end

Location & employment
On-site Melbourne CBD. Full-time permanent.
Salary $140,000–$165,000 AUD.
""".strip()


@dataclass(frozen=True)
class EvalCase:
    key: str
    label: str
    category: str
    posting_factory: Callable[[], JobPosting]


EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        key="applied-ai",
        label="Applied AI Engineer (strong AI Engineering fit)",
        category="strong_ai_fit",
        posting_factory=posting_applied_ai_engineer,
    ),
    EvalCase(
        key="senior-ai-production",
        label="Senior AI Engineer (commercial production AI required)",
        category="production_ai_required",
        posting_factory=posting_ai_engineer,
    ),
    EvalCase(
        key="data-engineer",
        label="Data Engineer (broad role, partial AI relevance)",
        category="broad_mixed_fit",
        posting_factory=posting_data_engineer,
    ),
    EvalCase(
        key="no-technologies",
        label="AI Engineer sparse spec (no named technologies)",
        category="no_named_technologies",
        posting_factory=posting_no_technologies,
    ),
    EvalCase(
        key="linkedin-production-rights",
        label="LinkedIn AI Engineer (production AI + working rights + on-site)",
        category="production_and_working_rights",
        posting_factory=lambda: JobPosting(
            title="AI Engineer",
            company="Discovered People",
            raw_text=LINKEDIN_PRODUCTION_AI_JOB_TEXT,
        ),
    ),
    EvalCase(
        key="developer-programmer",
        label="Developer Programmer SEEK (broad stack, salary friction)",
        category="commercial_friction",
        posting_factory=lambda: JobPosting(
            title="Developer Programmer",
            company="Example Enterprise Client",
            raw_text=DEVELOPER_PROGRAMMER_JOB_TEXT,
        ),
    ),
    EvalCase(
        key="contract-hybrid",
        label="Contract AI Engineer (contract + Sydney hybrid)",
        category="commercial_friction",
        posting_factory=posting_contract,
    ),
    EvalCase(
        key="missing-salary",
        label="AI Engineer (salary unstated)",
        category="salary_unknown",
        posting_factory=posting_missing_salary,
    ),
)


def _print_header(case: EvalCase) -> None:
    print("=" * 72)
    print(f"Case: {case.key}")
    print(f"Label: {case.label}")
    print(f"Category: {case.category}")
    print(f"Extraction prompt: {EXTRACTION_PROMPT_VERSION}")
    print(f"Assessment prompt: {ASSESSMENT_PROMPT_VERSION}")
    print("=" * 72)


def _print_assessment(assessment: OpportunityAssessment) -> None:
    payload = assessment.model_dump(mode="json")
    print(json.dumps(payload, indent=2))

    print("\nDimension judgments:")
    print(f"  technical:  {assessment.technical_fit.judgment}")
    print(f"  commercial: {assessment.commercial_fit.judgment}")
    print(f"  portfolio:  {assessment.portfolio_fit.judgment}")

    print("\nFinding kinds by dimension:")
    for name, dimension in (
        ("technical", assessment.technical_fit),
        ("commercial", assessment.commercial_fit),
        ("portfolio", assessment.portfolio_fit),
    ):
        kinds = [finding.kind for finding in dimension.findings]
        print(f"  {name}: {kinds}")

    print("\nProfile evidence refs:")
    for name, dimension in (
        ("technical", assessment.technical_fit),
        ("commercial", assessment.commercial_fit),
        ("portfolio", assessment.portfolio_fit),
    ):
        refs = [
            ref.ref
            for finding in dimension.findings
            for ref in finding.profile_evidence
        ]
        print(f"  {name}: {refs}")

    print("\nSummary:")
    print(f"  {assessment.summary.summary}")


def _run_case(case: EvalCase) -> str:
    """Run one evaluation case. Returns PASS, PARTIAL, or FAIL."""
    _print_header(case)
    posting = case.posting_factory()
    profile = CareerProfileService().load()
    analysis_service = JobAnalysisService(OpenAIJobExtractor())
    assessment_service = OpportunityAssessmentService(OpenAIAssessor())

    try:
        print("\nStep 1: Live JobAnalysis extraction...")
        job_analysis = analysis_service.analyse(posting)
        print(
            f"  role_family={job_analysis.role_family.family} "
            f"seniority={job_analysis.seniority.level} "
            f"technologies={len(job_analysis.technologies)} "
            f"compensation={job_analysis.compensation.clarity}"
        )

        print("\nStep 2: Live OpportunityAssessment...")
        assessment = assessment_service.assess(job_analysis, profile)
        print("\nAssessment succeeded.\n")
        _print_assessment(assessment)

        forbidden = (
            "tier",
            "platinum",
            "apply",
            "skip",
            "quota",
            "effort",
            "interview_probability",
        )
        serialised = json.dumps(assessment.model_dump(mode="json")).lower()
        leaked = [token for token in forbidden if token in serialised]
        if leaked:
            print(f"\nCHECK: possible forbidden tokens in output: {leaked}")
            return "FAIL"

        print("\nCHECK: validation passed; no forbidden tokens detected in serialised output.")
        return "PASS"

    except OpportunityAssessmentValidationError as error:
        print("\nVALIDATION FAILURE:")
        for detail in error.errors:
            print(f"  loc={detail.loc} type={detail.type} msg={detail.msg}")
        return "FAIL"
    except OpportunityAssessmentError as error:
        print(f"\nASSESSMENT ERROR: {error}")
        return "FAIL"
    except Exception:
        print("\nUNEXPECTED ERROR:")
        traceback.print_exc()
        return "FAIL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FR-003 live OpenAI assessment evaluation")
    parser.add_argument(
        "--case",
        help="Run a single case key (see --list)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available evaluation cases",
    )
    args = parser.parse_args(argv)

    if args.list:
        for case in EVAL_CASES:
            print(f"{case.key:28} {case.category:28} {case.label}")
        return 0

    cases = EVAL_CASES
    if args.case:
        matches = [case for case in EVAL_CASES if case.key == args.case]
        if not matches:
            print(f"Unknown case: {args.case}", file=sys.stderr)
            return 2
        cases = tuple(matches)

    results: list[tuple[str, str]] = []
    for case in cases:
        outcome = _run_case(case)
        results.append((case.key, outcome))
        print(f"\nRESULT: {case.key} -> {outcome}\n")

    print("=" * 72)
    print("Summary")
    for key, outcome in results:
        print(f"  {key}: {outcome}")

    failed = sum(1 for _, outcome in results if outcome == "FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
