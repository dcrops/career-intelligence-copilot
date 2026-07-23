"""Profile baseline sections rendered on every TailoredCv (not tailored).

Architectural choice (FR-006 validation support — Option A):

Active certifications are a **fixed profile baseline**, not TailoringPlan content.
They are always copied from the career profile's active certifications in profile
order. The Tailoring Plan does not select, order, or deprioritise certifications.

Rationale (smallest coherent fix):
- Certifications rarely need per-job reordering for Horizon 1 AI Engineering roles.
- Putting them on the Tailoring Plan would expand plan surface without dual-value.
- Fidelity validation therefore covers plan-owned sections only (skills, projects,
  experience guidance, summary themes). Certifications are owned by the profile
  baseline helper below, not by emphasis policy.

Do not invent certifications. Do not promote expired credentials.
"""

from __future__ import annotations

from career_intelligence.profile.models import CareerProfile


def active_certifications_baseline(profile: CareerProfile) -> list[dict[str, object]]:
    """Return active certifications in profile order for baseline CV rendering.

    This is intentionally **not** a TailoringPlan decision. Expired certifications
    are omitted from the baseline draft (they remain on the profile record).
    """
    return [
        {
            "certification_id": cert.id,
            "name": cert.name,
            "issuer": cert.issuer,
            "status": cert.status,
        }
        for cert in profile.certifications
        if cert.status == "active"
    ]


CERTIFICATIONS_BASELINE_ASSUMPTION = (
    "Certifications are rendered as a fixed profile baseline (active credentials "
    "only, profile order). They are not TailoringPlan-tailored content."
)
