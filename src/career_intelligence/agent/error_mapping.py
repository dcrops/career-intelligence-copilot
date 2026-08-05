"""Map adapter/service errors to owner-facing AgentStopReason (presentation layer).

Does not change ToolPolicy, allow-list, or underlying FR-006/007/011 service behaviour.
"""

from __future__ import annotations

from .types import AgentStopReason

_MATERIAL_BENEFIT_MARKERS: tuple[str, ...] = (
    "material-benefit",
    "material_benefit",
    "override_material_benefit",
    "consider_cv_tailoring",
)


def stop_reason_for_adapter_error(error: BaseException) -> AgentStopReason:
    """Classify an adapter failure into a dedicated stop reason when recognizable."""
    message = str(error).lower()
    if any(marker in message for marker in _MATERIAL_BENEFIT_MARKERS):
        return "material_benefit_required"
    return "unexpected_failure"
