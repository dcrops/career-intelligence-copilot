"""Confirmed duplicate group projection (FR-009 M3).

Groups are derived by scanning ``Opportunity.duplicate`` links, exactly as the review
queue derives ordering. There is no persisted group aggregate, so the Opportunity
store stays the single source of truth.
"""

from __future__ import annotations

from career_intelligence.opportunities.models import Opportunity

from .models import DuplicateGroup


def build_groups(records: list[Opportunity]) -> tuple[DuplicateGroup, ...]:
    """Group confirmed duplicates by canonical id, canonical id ascending.

    Records with no confirmed relation and no members form no group: a single
    advertisement is not a duplicate group of one.
    """
    members: dict[str, list[str]] = {}
    for record in records:
        if record.duplicate is None:
            continue
        members.setdefault(record.duplicate.duplicate_of, []).append(
            record.opportunity_id
        )

    return tuple(
        DuplicateGroup(
            canonical_opportunity_id=canonical_id,
            member_opportunity_ids=tuple(sorted(member_ids)),
        )
        for canonical_id, member_ids in sorted(members.items())
    )


def group_for(
    opportunity_id: str,
    records: list[Opportunity],
) -> DuplicateGroup | None:
    """The confirmed group containing ``opportunity_id``, or None if unlinked."""
    for group in build_groups(records):
        if opportunity_id in group.opportunity_ids:
            return group
    return None
