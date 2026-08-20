"""Shared factual evidence bundle for CIC and the strong LLM baseline.

Facts (candidate + employer + truth boundaries) are shared.
CIC selection/policy (argument spine, selected sources, trajectory mode as
a writer instruction) is excluded from the baseline payload.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from career_intelligence.cv_generation.master_adapt import (
    extract_h2_section,
    extract_master_highlights,
    extract_master_project_bodies,
    extract_master_summary,
    load_master_cv_markdown,
)
from career_intelligence.document_positioning.benchmark.jobs import (
    CAREER_PROFILE_PATH,
    MASTER_CV_PATH,
    FrozenEvalJob,
    load_advertisement,
    load_job_analysis,
)
from career_intelligence.document_positioning.benchmark.protocol import CIC_POLICY_KEYS
from career_intelligence.document_positioning.builder import build_positioning_plan
from career_intelligence.document_positioning.models import SupportStatus
from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile

_STATUS = {
    SupportStatus.SUPPORTED_DIRECT: "DIRECT",
    SupportStatus.SUPPORTED_RELATED: "RELATED",
    SupportStatus.UNSUPPORTED: "UNSUPPORTED",
}


class BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


class ClassifiedEmployerNeedFact(BundleModel):
    """Employer requirement plus catalogue classification. Not a candidate claim."""

    rank: int
    kind: str
    label: str
    level: str | None = None
    excerpt: str | None = None
    status: str
    requested_identity: str | None = None
    promotable_profile_label: str | None = None
    may_claim_requested: bool
    rationale: str
    supporting_profile_refs: tuple[str, ...] = ()


class ForbiddenClaimFact(BundleModel):
    requested_label: str
    may_not_claim: str
    reason: str
    identity: str | None = None


class TruthBoundaries(BundleModel):
    """Candidate-truth constraints that both generators must obey."""

    forbidden_claims: tuple[ForbiddenClaimFact, ...]
    claimable_direct_labels: tuple[str, ...]
    related_profile_labels: tuple[str, ...]
    unsupported_labels: tuple[str, ...]
    rules: tuple[str, ...] = (
        "Employer requirements are not candidate capabilities.",
        "AWS evidence does not mean AWS Bedrock experience.",
        "RAG evidence does not mean chatbot experience.",
        "RAG evidence does not automatically mean generic LLM evidence "
        "unless LLM evidence exists separately.",
        "Java does not mean JavaScript.",
        "Project experience does not automatically become commercial employment.",
        "Do not invent employers, responsibilities, dates, years, metrics, "
        "technologies, production usage, commercial experience, certifications, "
        "or project capabilities.",
        "RELATED: promote the candidate's real related capability; never claim "
        "the employer's requested identity.",
        "UNSUPPORTED identities may appear only as honest gaps, never as candidate claims.",
    )


class FactualEvidenceBundle(BundleModel):
    """Authority for both A and B. Hash this object for reproducibility."""

    job_id: str
    job_name: str
    company: str
    role_title: str
    role_family: str
    advertisement_text: str
    employer_needs: tuple[ClassifiedEmployerNeedFact, ...]
    candidate_profile: dict[str, Any]
    master_summary: str
    master_highlights: tuple[str, ...]
    master_project_bodies: dict[str, str]
    master_experience: str | None = None
    master_methodology: str | None = None
    master_courses: str | None = None
    master_certifications: str | None = None
    master_contact_header: str | None = None
    truth: TruthBoundaries
    profile_path: str
    master_cv_path: str
    analysis_path: str
    advertisement_path: str


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def bundle_hash(bundle: FactualEvidenceBundle) -> str:
    payload = bundle.model_dump(mode="json")
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return digest


def baseline_payload(bundle: FactualEvidenceBundle) -> dict[str, Any]:
    """JSON given to the baseline writer. Must not contain CIC policy keys."""
    return {
        "job": {
            "job_id": bundle.job_id,
            "job_name": bundle.job_name,
            "company": bundle.company,
            "role_title": bundle.role_title,
            "role_family": bundle.role_family,
            "advertisement_text": bundle.advertisement_text,
            "employer_needs": [item.model_dump(mode="json") for item in bundle.employer_needs],
            "note": (
                "employer_needs describe the job. They are not candidate capabilities."
            ),
        },
        "candidate": {
            "profile": bundle.candidate_profile,
            "master_summary": bundle.master_summary,
            "master_highlights": list(bundle.master_highlights),
            "master_project_bodies": bundle.master_project_bodies,
            "master_experience": bundle.master_experience,
            "master_methodology": bundle.master_methodology,
            "master_courses": bundle.master_courses,
            "master_certifications": bundle.master_certifications,
            "master_contact_header": bundle.master_contact_header,
        },
        "truth_boundaries": bundle.truth.model_dump(mode="json"),
    }


def payload_contains_cic_policy(payload: dict[str, Any]) -> list[str]:
    encoded = canonical_json(payload)
    hits = [key for key in sorted(CIC_POLICY_KEYS) if f'"{key}"' in encoded]
    return hits


def build_factual_evidence_bundle(
    job: FrozenEvalJob,
    *,
    profile: CareerProfile | None = None,
    master_markdown: str | None = None,
) -> FactualEvidenceBundle:
    bound_profile = profile or CareerProfileService.from_path(CAREER_PROFILE_PATH).load()
    master = master_markdown if master_markdown is not None else load_master_cv_markdown(
        MASTER_CV_PATH
    )
    analysis = load_job_analysis(job)
    advertisement = load_advertisement(job)
    plan = build_positioning_plan(analysis, bound_profile)
    needs: list[ClassifiedEmployerNeedFact] = []
    claimable: list[str] = []
    related: list[str] = []
    unsupported: list[str] = []
    for item in plan.employer_needs:
        status = _STATUS[item.classification.status]
        needs.append(
            ClassifiedEmployerNeedFact(
                rank=item.need.rank,
                kind=item.need.kind,
                label=item.need.label,
                level=item.need.level,
                excerpt=item.need.excerpt,
                status=status,
                requested_identity=item.classification.requested_identity,
                promotable_profile_label=item.classification.promotable_profile_label,
                may_claim_requested=item.classification.may_claim_requested,
                rationale=item.classification.rationale,
                supporting_profile_refs=tuple(ref.ref for ref in item.evidence_refs),
            )
        )
        if (
            item.classification.status is SupportStatus.SUPPORTED_DIRECT
            and item.classification.may_claim_requested
        ):
            claimable.append(
                item.classification.promotable_profile_label or item.need.label
            )
        elif (
            item.classification.status is SupportStatus.SUPPORTED_RELATED
            and item.classification.promotable_profile_label
        ):
            related.append(item.classification.promotable_profile_label)
        elif item.classification.status is SupportStatus.UNSUPPORTED:
            unsupported.append(item.need.label)
    forbidden = tuple(
        ForbiddenClaimFact(
            requested_label=item.requested_label,
            may_not_claim=item.may_not_claim,
            reason=item.reason,
            identity=item.identity,
        )
        for item in plan.forbidden_claims
    )
    header = master.split("\n## ", 1)[0].strip()
    return FactualEvidenceBundle(
        job_id=job.job_id,
        job_name=job.name,
        company=analysis.posting.company or "Unknown company",
        role_title=analysis.posting.title or job.name,
        role_family=analysis.role_family.family,
        advertisement_text=advertisement,
        employer_needs=tuple(needs),
        candidate_profile=_candidate_profile_dump(bound_profile),
        master_summary=extract_master_summary(master) or bound_profile.identity.summary or "",
        master_highlights=tuple(extract_master_highlights(master)),
        master_project_bodies=extract_master_project_bodies(master),
        master_experience=extract_h2_section(master, "professional experience"),
        master_methodology=extract_h2_section(master, "ai engineering methodology"),
        master_courses=extract_h2_section(master, "courses & upskilling"),
        master_certifications=extract_h2_section(master, "certifications"),
        master_contact_header=header or None,
        truth=TruthBoundaries(
            forbidden_claims=forbidden,
            claimable_direct_labels=tuple(dict.fromkeys(claimable)),
            related_profile_labels=tuple(dict.fromkeys(related)),
            unsupported_labels=tuple(dict.fromkeys(unsupported)),
        ),
        profile_path=str(CAREER_PROFILE_PATH),
        master_cv_path=str(MASTER_CV_PATH),
        analysis_path=str(job.analysis_path),
        advertisement_path=str(job.advertisement_path),
    )


def _candidate_profile_dump(profile: CareerProfile) -> dict[str, Any]:
    """Candidate facts only. Goals/preferences are owner intent, not evidence."""
    payload = profile.model_dump(mode="json")
    payload.pop("goals", None)
    payload.pop("preferences", None)
    return payload
