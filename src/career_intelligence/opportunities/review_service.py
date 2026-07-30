"""Owner review actions for durable Opportunities (FR-009 M2).

Writes review metadata and optional decision transitions through
``OpportunityService``. Does not touch pipeline status, FR-002–FR-005 artefact
snapshots, or ranking inputs. ``ReviewQueueService`` remains read-only.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pydantic import ValidationError

from .errors import (
    ErrorDetail,
    OpportunityTransitionError,
    OpportunityValidationError,
)
from .models import (
    Opportunity,
    OpportunityReview,
    OwnerDecisionRecord,
    ReviewActionKind,
    ReviewActionRecord,
)
from .service import OpportunityService

_PINNED_BY_ARCHIVE_DETAIL = "cleared pin on archive"
_CLEAR_DEFER_DETAIL = "cleared defer decision and defer_until"


class OpportunityReviewService:
    """Owner-authored review state changes against persisted Opportunities.

    Each method reloads immediately before writing, mutates only the fields the
    action owns, appends one ``ReviewActionRecord``, and persists through
    ``OpportunityService.replace``. Harmless repeats are idempotent; contradictory
    combinations raise ``OpportunityTransitionError``.
    """

    def __init__(self, opportunities: OpportunityService) -> None:
        self._opportunities = opportunities

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def mark_reviewed(
        self,
        opportunity_id: str,
        *,
        reviewed_at: datetime | None = None,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Record that the owner inspected this Opportunity.

        Does not create or change an owner decision. Repeating preserves the
        original ``reviewed_at``.
        """
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        if current.review.reviewed_at is not None:
            return current

        when = reviewed_at or stamp
        review = current.review.model_copy(update={"reviewed_at": when})
        return self._commit(
            current,
            review=review,
            decision=current.decision,
            action="mark_reviewed",
            occurred_at=stamp,
            detail=None,
            updated_at=stamp,
        )

    def pin(
        self,
        opportunity_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Mark the Opportunity for presentation prominence in the review queue."""
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        if current.review.archived_at is not None:
            raise OpportunityTransitionError(
                f"Cannot pin archived opportunity '{opportunity_id}'; "
                "reopen it first"
            )
        if current.review.pinned:
            return current
        review = current.review.model_copy(update={"pinned": True})
        return self._commit(
            current,
            review=review,
            decision=current.decision,
            action="pin",
            occurred_at=stamp,
            detail=None,
            updated_at=stamp,
        )

    def unpin(
        self,
        opportunity_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Clear presentation prominence."""
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        if not current.review.pinned:
            return current
        review = current.review.model_copy(update={"pinned": False})
        return self._commit(
            current,
            review=review,
            decision=current.decision,
            action="unpin",
            occurred_at=stamp,
            detail=None,
            updated_at=stamp,
        )

    def defer_until(
        self,
        opportunity_id: str,
        until: date,
        *,
        reference_date: date | None = None,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Defer review until ``until`` (exclusive of expiry on that date).

        Sets ``decision=defer`` when the record is undecided or already deferred.
        Refuses to overwrite ``apply`` / ``skip``. Rejects a date strictly before
        ``reference_date`` (defaults to today, UTC). Same-day is allowed and means
        the defer has already expired for that reference date.
        """
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        as_at = reference_date or stamp.date()
        if until < as_at:
            raise OpportunityValidationError(
                [
                    ErrorDetail(
                        loc=("until",),
                        msg=(
                            f"defer_until {until.isoformat()} is before "
                            f"reference_date {as_at.isoformat()}"
                        ),
                        type="value_error",
                    )
                ]
            )

        decision_kind = current.decision.decision if current.decision else None
        if decision_kind in {"apply", "skip"}:
            raise OpportunityTransitionError(
                f"Cannot defer opportunity '{opportunity_id}' with "
                f"decision={decision_kind!r}; clear or change that decision first"
            )

        if decision_kind == "defer":
            decision = current.decision
        else:
            decision = OwnerDecisionRecord(decision="defer", decided_at=stamp)

        # Idempotent when the date is unchanged and decision is already defer.
        if (
            current.review.defer_until == until
            and decision_kind == "defer"
            and current.decision is not None
        ):
            return current

        review = current.review.model_copy(update={"defer_until": until})
        return self._commit(
            current,
            review=review,
            decision=decision,
            action="defer_until",
            occurred_at=stamp,
            detail=until.isoformat(),
            updated_at=stamp,
        )

    def clear_defer(
        self,
        opportunity_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Bring a deferred Opportunity back early as undecided.

        Clears ``defer_until`` and the ``defer`` owner decision. Does not invent
        apply or skip. No-op when neither a defer decision nor a defer date is set.
        """
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        decision_kind = current.decision.decision if current.decision else None
        has_defer = decision_kind == "defer" or current.review.defer_until is not None
        if not has_defer:
            return current

        if decision_kind not in {None, "defer"}:
            raise OpportunityTransitionError(
                f"Cannot clear defer on opportunity '{opportunity_id}' with "
                f"decision={decision_kind!r}"
            )

        review = current.review.model_copy(update={"defer_until": None})
        return self._commit(
            current,
            review=review,
            decision=None,
            action="clear_defer",
            occurred_at=stamp,
            detail=_CLEAR_DEFER_DETAIL,
            updated_at=stamp,
        )

    def archive(
        self,
        opportunity_id: str,
        *,
        archived_at: datetime | None = None,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Hide the Opportunity from default review views.

        Automatically clears ``pinned`` so the archived-not-pinned invariant holds.
        Repeating preserves the original ``archived_at``.
        """
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        if current.review.archived_at is not None:
            return current

        when = archived_at or stamp
        cleared_pin = current.review.pinned
        review = current.review.model_copy(
            update={"archived_at": when, "pinned": False}
        )
        return self._commit(
            current,
            review=review,
            decision=current.decision,
            action="archive",
            occurred_at=stamp,
            detail=_PINNED_BY_ARCHIVE_DETAIL if cleared_pin else None,
            updated_at=stamp,
        )

    def reopen(
        self,
        opportunity_id: str,
        *,
        occurred_at: datetime | None = None,
    ) -> Opportunity:
        """Restore review visibility by clearing ``archived_at`` only.

        Does not clear owner decision, defer, duplicate, pin, or reviewed_at.
        """
        current = self._opportunities.get(opportunity_id)
        stamp = occurred_at or datetime.now(UTC)
        if current.review.archived_at is None:
            return current
        review = current.review.model_copy(update={"archived_at": None})
        return self._commit(
            current,
            review=review,
            decision=current.decision,
            action="reopen",
            occurred_at=stamp,
            detail=None,
            updated_at=stamp,
        )

    def _commit(
        self,
        current: Opportunity,
        *,
        review: OpportunityReview,
        decision: OwnerDecisionRecord | None,
        action: ReviewActionKind,
        occurred_at: datetime,
        detail: str | None,
        updated_at: datetime,
    ) -> Opportunity:
        try:
            entry = ReviewActionRecord(
                action=action,
                occurred_at=occurred_at,
                detail=detail,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        try:
            updated = current.model_copy(
                update={
                    "review": review,
                    "decision": decision,
                    "review_actions": (*current.review_actions, entry),
                    "updated_at": updated_at,
                },
                deep=True,
            )
        except ValidationError as error:
            raise OpportunityValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error

        return self._opportunities.replace(updated)
