"""Render M4 bounded cover-letter positioning inspection for the four frozen jobs.

Uses the fixture composer (no OpenAI). Does not write live application packages.
Does not wire PositioningPlan into cic package prepare.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.document_positioning import (
    BoundedCoverLetterPositioningService,
    FixtureCoverLetterPositioningComposer,
    SupportStatus,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile

REPO = Path(__file__).resolve().parents[1]


def _job(path: Path) -> JobAnalysis:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "job_analysis.json":
        return JobAnalysis.model_validate(payload)
    return JobAnalysis.model_validate(payload["job_analysis"])


def _strategy(job: JobAnalysis, profile: CareerProfile, source: Path) -> ApplicationStrategy:
    payload = json.loads(source.read_text(encoding="utf-8"))
    emphasis = None
    if source.name != "job_analysis.json":
        raw = payload.get("application_strategy")
        if isinstance(raw, dict) and raw.get("portfolio_emphasis"):
            emphasis = raw["portfolio_emphasis"]
    if not emphasis:
        emphasis = [
            {
                "project_id": project.id,
                "source_rank": index,
                "summary": project.summary or project.name,
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": project.id,
                    }
                ],
            }
            for index, project in enumerate(profile.projects, start=1)
        ]
    return ApplicationStrategy.model_validate(
        {
            "application_tier": "platinum",
            "pursuit_posture": "prioritise",
            "practical_value": "career_priority",
            "effort_level": "full",
            "summary": "Inspection-only strategy wrapper; not a production package.",
            "reasons": [
                {
                    "kind": "alignment",
                    "summary": "Inspection wrapper.",
                    "importance": "material",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "risks_or_gaps": [
                {
                    "summary": "Inspection wrapper.",
                    "importance": "minor",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {"source": "compensation"},
                        }
                    ],
                }
            ],
            "manual_checks": [
                {
                    "summary": "Inspection wrapper.",
                    "why_it_matters": "Not used for generation.",
                    "could_change_recommendation": False,
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {"source": "compensation"},
                        }
                    ],
                }
            ],
            "next_actions": [
                {
                    "kind": "consider_owner_review",
                    "summary": "Inspection only.",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "portfolio_emphasis": emphasis,
            "assumptions": ["Inspection wrapper."],
            "decision_blockers": [],
            "owner_review_required": True,
            "insufficient_information": False,
            "job_analysis": job,
        }
    )


def _status_line(pack) -> list[str]:
    lines = ["### DIRECT / RELATED / UNSUPPORTED", ""]
    for item in pack.employer_needs:
        status = {
            SupportStatus.SUPPORTED_DIRECT: "DIRECT",
            SupportStatus.SUPPORTED_RELATED: "RELATED",
            SupportStatus.UNSUPPORTED: "UNSUPPORTED",
        }[item.status]
        extra = ""
        if item.status is SupportStatus.SUPPORTED_RELATED:
            extra = f" (promote {item.promotable_profile_label}; may_claim_requested=False)"
        lines.append(f"- **{item.label}** → {status}{extra}")
    return lines


def main() -> None:
    profile = CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()
    service = BoundedCoverLetterPositioningService(
        FixtureCoverLetterPositioningComposer()
    )
    jobs = [
        (
            "E1 — Allura AI Engineer",
            REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
            "AI-lead opening. Python/REST/LLM DIRECT. GCP/MLOps/DevOps unclaimed. Testing history only if useful.",
        ),
        (
            "E2 — CSK mixed-fit specialist",
            REPO
            / "tests"
            / "fixtures"
            / "document_positioning"
            / "eval_jobs"
            / "02_csk_mixed_fit"
            / "job_analysis.json",
            "RAG / AI application lead. AWS RELATED for Bedrock; Bedrock and chatbot unclaimed.",
        ),
        (
            "E3 — Maincode AI Infrastructure",
            REPO
            / "manual_validation"
            / "outputs"
            / "012_maincode_ai_infrastructure_engineer.json",
            "Stretch-control. GPU/Linux/HPC stay gaps. Do not present as an infrastructure engineer.",
        ),
        (
            "E4 — Repurpose AI Adoption Specialist",
            REPO
            / "manual_validation"
            / "outputs"
            / "008_repurpose_it_ai_adoption_specialist.json",
            "full_chapters. QA → DE → AI useful. Copilot/Claude unclaimed.",
        ),
    ]
    parts = [
        "# Document Positioning M4 — Four-job cover-letter positioning inspection",
        "",
        "Offline inspection with `FixtureCoverLetterPositioningComposer`. Not live OpenAI. "
        "Not production `cic package prepare`. Not an M5 A/B evaluation. "
        "CSK live application package was not regenerated.",
        "",
        "Shared candidate evidence: `data/career_profile.yaml`.",
        "",
        "PortfolioMatch ranks use frozen golden `application_strategy.portfolio_emphasis` "
        "for E1/E3/E4. E2's tracked freeze is job analysis only, so emphasis falls "
        "back to live CareerProfile project order.",
        "",
        "---",
        "",
    ]
    for title, path, why in jobs:
        job = _job(path)
        result = service.compose(job, profile, strategy=_strategy(job, profile, path))
        pack = result.pack
        parts.append(f"# {title}")
        parts.append("")
        parts.append(why)
        parts.append("")
        parts.append("## Employer needs")
        parts.append("")
        parts.extend(_status_line(pack))
        parts.append("")
        parts.append("## Selected evidence sources")
        parts.append("")
        for source in pack.selected_sources:
            covered = ", ".join(source.employer_needs_covered) or "none listed"
            rank = (
                f"PortfolioMatch rank {source.portfolio_match_rank}"
                if source.portfolio_match_rank is not None
                else "no PortfolioMatch rank"
            )
            parts.append(f"- **{source.name}** (`{source.source_id}`, {source.source_type})")
            parts.append(f"  - Why selected: {source.purpose}")
            parts.append(f"  - Employer need(s) covered: {covered}")
            parts.append(f"  - {rank}")
            if source.override_reason:
                parts.append(f"  - Override: {source.override_reason}")
        if pack.portfolio_overrides:
            parts.append("")
            parts.append("## PortfolioMatch overrides")
            parts.append("")
            for item in pack.portfolio_overrides:
                parts.append(
                    f"- Rank {item.portfolio_match_rank} `{item.project_id}` "
                    f"({item.project_name}): {item.reason}"
                )
        else:
            parts.append("")
            parts.append("## PortfolioMatch overrides")
            parts.append("")
            parts.append("- None for this job.")
        parts.append("")
        parts.append("## Trajectory / forbidden claims")
        parts.append("")
        parts.append(f"- **trajectory_mode:** `{pack.trajectory_mode}`")
        parts.append(f"- {pack.trajectory_rationale}")
        parts.append("- **Forbidden claims:**")
        for item in pack.forbidden_claims[:12]:
            parts.append(f"  - {item.may_not_claim} ({item.reason})")
        parts.append("")
        parts.append("## Generated fixture cover letter")
        parts.append("")
        for paragraph in result.paragraphs:
            parts.append(paragraph)
            parts.append("")
        parts.append("## Validation")
        parts.append("")
        parts.append("Composer output passed M4 deterministic validators (fail-closed).")
        parts.append("FR-014 was **not** run; this is not package Truth PASS.")
        parts.append("")
        parts.append("---")
        parts.append("")
    parts.extend(
        [
            "# Quality notes (fixture inspection, not M5)",
            "",
            "- The fixture writer is pack-faithful and explicit. That is useful for "
            "validating policy and commercially weak. Do not treat fixture wording as "
            "recruiter-quality or as M5 preference evidence.",
            "- Openings name the employer/role family and packed DIRECT capabilities. "
            "They avoid 'I am excited to apply'. They are still formulaic.",
            "- E1 leads with AI evidence rather than a QA → DE → AI biography. "
            "GCP/MLOps/DevOps are not claimed. Related ADF/data-pipeline evidence is "
            "not forced into the letter when it is a late RELATED need. Rank-1 "
            "Public Holiday Entitlements is overridden because RAG/OIC cover more "
            "DIRECT needs. CIC is not the second source because it lacks FastAPI/"
            "REST overlap; that is inspectable coverage, not a ranking accident.",
            "- E2 selects Governance RAG for DIRECT RAG/Python and nbn AWS employment "
            "for RELATED Bedrock coverage. Bedrock and chatbot are not claimed. "
            "The raw posting title (which lists Bedrock and Chatbots) is not pasted "
            "into prose; `prose_role_title` falls back to the role family.",
            "- E3 does not claim GPU/Linux/HPC. It still surfaces truthful AI/Python "
            "portfolio evidence because those are authorised CareerProfile sources. "
            "That is not invented infrastructure employment, but the letter can still "
            "look stronger than a stretch role warrants. Watch this at M5.",
            "- E4 uses `full_chapters`. Copilot/Claude are not claimed. Portfolio "
            "evidence supports the trajectory rather than replacing it.",
            "- Evidence-source count is two by default; a third source appears only "
            "when a remaining high-priority DIRECT/RELATED need is uncovered.",
            "- Production `cic package prepare` still uses the pre-M4 bounded "
            "cover-letter path (`BoundedCoverLetterService` + tag/concern project "
            "selection). M4 is implemented and unwired. M6 owns production integration.",
            "",
        ]
    )
    out = REPO / "docs" / "eval" / "document_positioning_m4_inspection.md"
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
