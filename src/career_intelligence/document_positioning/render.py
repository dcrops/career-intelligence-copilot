"""Human-readable PositioningPlan inspection (not production document generation)."""

from __future__ import annotations

from career_intelligence.document_positioning.models import (
    PositioningPlan,
    SupportStatus,
)


def render_positioning_plan(title: str, plan: PositioningPlan) -> str:
    """Render an owner-review inspection of one PositioningPlan."""
    lines = [f"# {title}", ""]
    lines.extend(_section_needs(plan))
    lines.extend(_section_by_status(plan, SupportStatus.SUPPORTED_DIRECT, "DIRECT"))
    lines.extend(_section_by_status(plan, SupportStatus.SUPPORTED_RELATED, "RELATED"))
    lines.extend(_section_by_status(plan, SupportStatus.UNSUPPORTED, "UNSUPPORTED"))
    lines.append("## Selected evidence")
    lines.append("")
    if plan.selected_evidence_refs:
        for ref in plan.selected_evidence_refs:
            lines.append(f"- `{ref.ref}` ({ref.source})")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Argument spine")
    lines.append("")
    for claim in plan.argument_spine:
        lines.append(f"- **{claim.kind}:** {claim.statement}")
    lines.append("")
    lines.append("## Forbidden claims")
    lines.append("")
    if plan.forbidden_claims:
        for item in plan.forbidden_claims:
            lines.append(
                f"- Must not claim **{item.may_not_claim}** "
                f"({item.reason}; requested '{item.requested_label}')"
            )
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## Trajectory and methodology")
    lines.append("")
    lines.append(f"- **trajectory_mode:** `{plan.trajectory_mode}`")
    lines.append(f"- {plan.trajectory_rationale}")
    lines.append(f"- **include_methodology:** `{plan.include_methodology}`")
    lines.append(f"- {plan.include_methodology_rationale}")
    lines.append("")
    lines.append("## Rewrite authority")
    lines.append("")
    lines.append(
        "- CV rewrite surface: "
        + ", ".join(plan.cv_rewrite_surface)
    )
    lines.append(
        "- Locked Master sections: "
        + ", ".join(plan.locked_master_sections)
    )
    lines.append("")
    return "\n".join(lines)


def _section_needs(plan: PositioningPlan) -> list[str]:
    lines = ["## Top employer needs", ""]
    for item in plan.employer_needs:
        need = item.need
        status = item.classification.status.value
        lines.append(
            f"{need.rank}. **{need.label}** ({need.kind}"
            f"{f', {need.level}' if need.level else ''}) → `{status}`"
        )
    lines.append("")
    return lines


def _section_by_status(
    plan: PositioningPlan,
    status: SupportStatus,
    heading: str,
) -> list[str]:
    lines = [f"## {heading} requirements", ""]
    matched = [
        item for item in plan.employer_needs if item.classification.status is status
    ]
    if not matched:
        lines.append("- None")
        lines.append("")
        return lines
    for item in matched:
        result = item.classification
        extra = ""
        if result.promotable_profile_label:
            extra = f" — promote `{result.promotable_profile_label}`"
        refs = ", ".join(ref.ref for ref in item.evidence_refs) or "no evidence refs"
        lines.append(f"- **{item.need.label}**{extra} ({refs})")
    lines.append("")
    return lines
