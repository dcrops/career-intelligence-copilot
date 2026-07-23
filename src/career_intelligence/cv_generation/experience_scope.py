"""Master-CV vs extended-history experience scope for FR-006.

===========================================================================
TEMPORARY OWNER-PROFILE RULE (not a domain-model invariant)
===========================================================================

The career profile includes pre-nbn employment / study entries that are absent
from the operational Master CV. Until FR-001 gains an explicit experience-scope
flag (out of scope for FR-006), FR-006 uses a **temporary, isolated allow-list
of experience ids** defined only in this module.

Replace later by:
- a profile-level ``on_master_cv`` / ``cv_scope`` field, or
- an owner-maintained YAML allow/deny list,

without changing TailoringPlanService or CvGenerationService call sites — only
``is_extended_history_experience_id`` / ``partition_experience_ids`` need to
change.

Source of truth for *why* these ids exist:
``docs/08_implementation_notes.md`` § Career-history refinement / pre-nbn history.

Do **not** duplicate this frozenset elsewhere in the codebase.
===========================================================================
"""

from __future__ import annotations

from career_intelligence.profile.models import CareerProfile, Identifier

# ---------------------------------------------------------------------------
# Temporary rule — single definition site. Do not copy these ids elsewhere.
# ---------------------------------------------------------------------------
_TEMPORARY_EXTENDED_HISTORY_EXPERIENCE_IDS: frozenset[str] = frozenset(
    {
        "general-assembly-data-science-2019",
        "bakers-delight-test-analyst-2019",
        "accesshq-test-analyst-2018",
        "bakers-delight-test-analyst-2015",
        "console-test-analyst-2012",
        "bakers-delight-test-analyst-2009",
    }
)


def temporary_extended_history_experience_ids() -> frozenset[str]:
    """Return the temporary extended-history id set (read-only copy semantics)."""
    return _TEMPORARY_EXTENDED_HISTORY_EXPERIENCE_IDS


def is_extended_history_experience_id(experience_id: str) -> bool:
    """True when ``experience_id`` is treated as extended (non-Master-CV) history."""
    return experience_id in _TEMPORARY_EXTENDED_HISTORY_EXPERIENCE_IDS


def partition_experience_ids(
    profile: CareerProfile,
    *,
    include_extended_history: bool,
) -> tuple[list[Identifier], list[Identifier]]:
    """Return (included_ids, excluded_ids) in profile experience order.

    Default (``include_extended_history=False``): Master-CV-aligned scope —
    temporary extended-history ids are excluded.
    """
    included: list[Identifier] = []
    excluded: list[Identifier] = []
    for entry in profile.experience:
        if include_extended_history or not is_extended_history_experience_id(entry.id):
            included.append(entry.id)
        else:
            excluded.append(entry.id)
    return included, excluded


# Backwards-compatible alias for tests/imports that referenced the old name.
# Prefer ``temporary_extended_history_experience_ids()`` or
# ``is_extended_history_experience_id`` in new code.
EXTENDED_HISTORY_EXPERIENCE_IDS: frozenset[str] = _TEMPORARY_EXTENDED_HISTORY_EXPERIENCE_IDS
