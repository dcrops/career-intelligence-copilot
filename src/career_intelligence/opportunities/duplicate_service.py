"""Owner duplicate confirmation, rejection and canonical selection (FR-009 M3).

Non-destructive by contract: nothing is merged, collapsed, or deleted. Confirming a
duplicate records a ``DuplicateRelation`` from the duplicate record to the canonical
record, so every discovered advertisement survives for provenance and recovery.

Detection and candidate scoring live in ``career_intelligence.duplicates`` and are
derived, never persisted. This module only writes owner-confirmed outcomes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from .errors import (
    ErrorDetail,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from .models import (
    DuplicateEvidenceKind,
    DuplicateRejection,
    DuplicateRelation,
    Opportunity,
    ReviewActionKind,
    ReviewActionRecord,
)
from .service import OpportunityService


class DuplicateReviewService:
    """Owner-confirmed duplicate relationships over persisted Opportunities.

    Group shape is a star: the canonical record carries no relation, and every
    confirmed member points at the canonical id. Chains are rejected, so a group
    is always exactly one hop deep and can be reconstructed by a single scan.
    """

    def __init__(self, opportunities: OpportunityService) -> None:
        self._opportunities = opportunities

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def confirm_duplicate(
        self,
        duplicate_id: str,
        canonical_id: str,
        *,
        evidence: tuple[DuplicateEvidenceKind, ...] = ("owner_judgment",),
        confirmed_at: datetime | None = None,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Link ``duplicate_id`` to ``canonical_id`` as the same real-world vacancy.

        Idempotent when the same link already exists (the original ``confirmed_at``
        is preserved). Raises when the pair is the same record, when either side
        would create a chain, or when the pair was previously rejected.
        """
        if duplicate_id == canonical_id:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("canonical_id",),
                        msg="a record cannot be a duplicate of itself",
                        type="value_error",
                    )
                ]
            )

        stamp = occurred_at or datetime.now(UTC)
        duplicate = self._opportunities.get(duplicate_id)
        canonical = self._opportunities.get(canonical_id)

        existing = duplicate.duplicate
        if existing is not None and existing.duplicate_of == canonical_id:
            return duplicate
        if existing is not None:
            raise OpportunityTransitionError(
                f"Opportunity '{duplicate_id}' is already a confirmed duplicate of "
                f"'{existing.duplicate_of}'; use confirm_canonical to move the group"
            )

        if self._is_rejected_pair(duplicate, canonical):
            raise OpportunityTransitionError(
                f"Pair '{duplicate_id}' / '{canonical_id}' was rejected as a "
                "duplicate; the rejection must be cleared before confirming"
            )

        if canonical.duplicate is not None:
            raise OpportunityTransitionError(
                f"Canonical '{canonical_id}' is itself a duplicate of "
                f"'{canonical.duplicate.duplicate_of}'; confirm against the "
                "canonical record instead"
            )

        if self._members_of(duplicate_id):
            raise OpportunityTransitionError(
                f"Opportunity '{duplicate_id}' is the canonical record of an "
                "existing group; use confirm_canonical to choose a new canonical"
            )

        try:
            relation = DuplicateRelation(
                duplicate_of=canonical_id,
                confirmed_at=confirmed_at or stamp,
                evidence=evidence,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        return self._commit(
            duplicate,
            updates={"duplicate": relation},
            action="confirm_duplicate",
            occurred_at=stamp,
            detail=f"duplicate_of={canonical_id}",
        )

    def reject_duplicate(
        self,
        opportunity_id: str,
        other_opportunity_id: str,
        *,
        note: str | None = None,
        rejected_at: datetime | None = None,
        occurred_at: datetime | None = None,
    ) -> tuple[Opportunity, Opportunity]:
        """Record that a suggested pair is **not** the same vacancy.

        Written on both records so the suggestion never reappears from either
        direction. Idempotent, and refuses to contradict a confirmed link.
        """
        if opportunity_id == other_opportunity_id:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("other_opportunity_id",),
                        msg="a record cannot be rejected against itself",
                        type="value_error",
                    )
                ]
            )

        stamp = occurred_at or datetime.now(UTC)
        first = self._opportunities.get(opportunity_id)
        second = self._opportunities.get(other_opportunity_id)

        if self._is_confirmed_pair(first, second):
            raise OpportunityTransitionError(
                f"Pair '{opportunity_id}' / '{other_opportunity_id}' is already a "
                "confirmed duplicate; it cannot be rejected without unlinking first"
            )

        when = rejected_at or stamp
        updated_first = self._record_rejection(
            first, other_opportunity_id, when=when, note=note, occurred_at=stamp
        )
        updated_second = self._record_rejection(
            second, opportunity_id, when=when, note=note, occurred_at=stamp
        )
        return updated_first, updated_second

    def confirm_canonical(
        self,
        canonical_id: str,
        *,
        evidence: tuple[DuplicateEvidenceKind, ...] = ("owner_judgment",),
        confirmed_at: datetime | None = None,
        occurred_at: datetime | None = None,
    ) -> list[Opportunity]:
        """Make ``canonical_id`` the canonical record of its existing group.

        Re-points every other member at ``canonical_id`` and clears the relation on
        the chosen record. Preserves all records. Idempotent when the group already
        has this canonical. Returns the group's records, canonical first.
        """
        stamp = occurred_at or datetime.now(UTC)
        chosen = self._opportunities.get(canonical_id)
        member_ids = self._group_member_ids(chosen)
        if not member_ids:
            raise OpportunityTransitionError(
                f"Opportunity '{canonical_id}' is not part of a confirmed duplicate "
                "group; confirm a duplicate link first"
            )

        current_canonical = (
            chosen.duplicate.duplicate_of if chosen.duplicate is not None else canonical_id
        )
        if current_canonical == canonical_id:
            return self._group_records(canonical_id, member_ids)

        when = confirmed_at or stamp
        for member_id in sorted(member_ids):
            record = self._opportunities.get(member_id)
            if member_id == canonical_id:
                self._commit(
                    record,
                    updates={"duplicate": None},
                    action="confirm_canonical",
                    occurred_at=stamp,
                    detail=f"canonical={canonical_id}",
                )
                continue
            try:
                relation = DuplicateRelation(
                    duplicate_of=canonical_id,
                    confirmed_at=(
                        record.duplicate.confirmed_at
                        if record.duplicate is not None
                        else when
                    ),
                    evidence=(
                        record.duplicate.evidence
                        if record.duplicate is not None and record.duplicate.evidence
                        else evidence
                    ),
                )
            except ValidationError as error:
                raise OpportunityValidationError(
                    [ErrorDetail.from_pydantic(item) for item in error.errors()]
                ) from error
            self._commit(
                record,
                updates={"duplicate": relation},
                action="confirm_canonical",
                occurred_at=stamp,
                detail=f"duplicate_of={canonical_id}",
            )

        return self._group_records(canonical_id, member_ids)

    def _group_member_ids(self, record: Opportunity) -> set[str]:
        """Ids of every record in ``record``'s confirmed group, including itself."""
        canonical_id = (
            record.duplicate.duplicate_of
            if record.duplicate is not None
            else record.opportunity_id
        )
        members = self._members_of(canonical_id)
        if not members and record.duplicate is None:
            return set()
        return {canonical_id, *members}

    def _members_of(self, canonical_id: str) -> set[str]:
        return {
            item.opportunity_id
            for item in self._opportunities.list_opportunities()
            if item.duplicate is not None
            and item.duplicate.duplicate_of == canonical_id
        }

    def _group_records(
        self, canonical_id: str, member_ids: set[str]
    ) -> list[Opportunity]:
        others = sorted(member_ids - {canonical_id})
        return [
            self._opportunities.get(canonical_id),
            *(self._opportunities.get(item) for item in others),
        ]

    @staticmethod
    def _is_rejected_pair(first: Opportunity, second: Opportunity) -> bool:
        return any(
            rejection.other_opportunity_id == second.opportunity_id
            for rejection in first.duplicate_rejections
        ) or any(
            rejection.other_opportunity_id == first.opportunity_id
            for rejection in second.duplicate_rejections
        )

    @staticmethod
    def _is_confirmed_pair(first: Opportunity, second: Opportunity) -> bool:
        return (
            first.duplicate is not None
            and first.duplicate.duplicate_of == second.opportunity_id
        ) or (
            second.duplicate is not None
            and second.duplicate.duplicate_of == first.opportunity_id
        )

    def _record_rejection(
        self,
        record: Opportunity,
        other_id: str,
        *,
        when: datetime,
        note: str | None,
        occurred_at: datetime,
    ) -> Opportunity:
        already = any(
            rejection.other_opportunity_id == other_id
            for rejection in record.duplicate_rejections
        )
        if already:
            return record
        try:
            rejection = DuplicateRejection(
                other_opportunity_id=other_id,
                rejected_at=when,
                note=note,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        return self._commit(
            record,
            updates={
                "duplicate_rejections": (*record.duplicate_rejections, rejection)
            },
            action="reject_duplicate",
            occurred_at=occurred_at,
            detail=f"not_duplicate_of={other_id}",
        )

    def _commit(
        self,
        current: Opportunity,
        *,
        updates: dict[str, object],
        action: ReviewActionKind,
        occurred_at: datetime,
        detail: str | None,
    ) -> Opportunity:
        try:
            entry = ReviewActionRecord(
                action=action,
                occurred_at=occurred_at,
                detail=detail,
            )
            candidate = current.model_copy(
                update={
                    **updates,
                    "review_actions": (*current.review_actions, entry),
                    "updated_at": occurred_at,
                },
                deep=True,
            )
            # model_copy skips validators, so re-validate before the write to keep
            # duplicate invariants (no self-link, no confirmed-and-rejected pair).
            updated = Opportunity.model_validate(candidate.model_dump())
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        return self._opportunities.replace(updated)
