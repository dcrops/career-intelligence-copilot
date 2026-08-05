"""Build ReadinessSnapshot from live CIC services (FR-015 M2).

Derived projection only — does not mutate Opportunity, package, truth, or pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.application_package.errors import (
    ApplicationPackageIntegrityError,
    ApplicationPackageNotFoundError,
)
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.gates import (
    PackageTruthStatus,
    evaluate_package_truth,
)
from career_intelligence.truth_validation.store import JsonDirectoryTruthReportStore

from .hashing import compute_snapshot_hash
from .models import (
    ArtefactPresence,
    PackageReadiness,
    ReadinessSnapshot,
    TruthReadiness,
)
from .types import PackageStatus, TruthStatus


class ReadinessBuilder(Protocol):
    def build(
        self,
        opportunity_id: str,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_id: str | None = None,
        prior_agent_run_incomplete: bool = False,
        clarification_required: bool = False,
        clarification_message: str | None = None,
        contradictory_flags: tuple[str, ...] = (),
        observed_at: datetime | None = None,
    ) -> ReadinessSnapshot: ...


class LiveReadinessBuilder:
    """Observe Opportunity + package + truth gates into a ReadinessSnapshot."""

    def __init__(
        self,
        opportunities: OpportunityService,
        packages: ApplicationPackageService,
        *,
        profile: CareerProfile,
        truth_store: JsonDirectoryTruthReportStore | None = None,
        truth_reports_root: Path | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._packages = packages
        self._profile = profile
        if truth_store is not None:
            self._truth_store = truth_store
        else:
            root = truth_reports_root
            if root is None:
                root = Path(__file__).resolve().parents[3] / "data" / "truth_reports"
            self._truth_store = JsonDirectoryTruthReportStore(root)

    def build(
        self,
        opportunity_id: str,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_id: str | None = None,
        prior_agent_run_incomplete: bool = False,
        clarification_required: bool = False,
        clarification_message: str | None = None,
        contradictory_flags: tuple[str, ...] = (),
        observed_at: datetime | None = None,
    ) -> ReadinessSnapshot:
        opportunity = self._opportunities.get(opportunity_id)
        paths = opportunity.artifact_paths or {}
        artefacts = ArtefactPresence(
            job_analysis="job_analysis.json" in paths,
            assessment="assessment.json" in paths,
            portfolio_match="portfolio_match.json" in paths,
            strategy="strategy.json" in paths,
        )
        decision = (
            opportunity.decision.decision if opportunity.decision is not None else None
        )
        package = self._observe_package(opportunity_id)
        truth = self._observe_truth(opportunity_id, package)
        stamp = observed_at or datetime.now(tz=UTC)
        snapshot = ReadinessSnapshot(
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            decision=decision,
            artefacts=artefacts,
            package=package,
            truth=truth,
            owner_approvals_present=owner_approvals_present,
            clarification_required=clarification_required,
            clarification_message=clarification_message,
            provider_available=provider_available,
            contradictory_flags=contradictory_flags,
            prior_agent_run_id=prior_agent_run_id,  # type: ignore[arg-type]
            prior_agent_run_incomplete=prior_agent_run_incomplete,
            observed_at=stamp,
        )
        return snapshot.model_copy(
            update={"snapshot_hash": compute_snapshot_hash(snapshot)}
        )

    def _observe_package(self, opportunity_id: str) -> PackageReadiness:
        if not self._packages.exists(opportunity_id):
            return PackageReadiness(status="absent")
        try:
            manifest = self._packages.get(opportunity_id, verify=True)
        except ApplicationPackageNotFoundError:
            return PackageReadiness(status="absent")
        except ApplicationPackageIntegrityError:
            # Manifest exists but drafts missing/corrupt.
            try:
                manifest = self._packages.get(opportunity_id, verify=False)
            except Exception:  # noqa: BLE001
                return PackageReadiness(
                    status="integrity_failed",
                    manifest_ref=f"package:{opportunity_id}",
                    cv_present=False,
                    cover_letter_present=False,
                )
            cv_ok = Path(manifest.cv.markdown_path).is_file()
            cl_ok = Path(manifest.cover_letter.markdown_path).is_file()
            return PackageReadiness(
                status="integrity_failed",
                manifest_ref=f"package:{opportunity_id}",
                cv_present=cv_ok,
                cover_letter_present=cl_ok,
            )

        cv_ok = Path(manifest.cv.markdown_path).is_file()
        cl_ok = Path(manifest.cover_letter.markdown_path).is_file()
        status: PackageStatus
        if cv_ok and cl_ok:
            status = "present"
        else:
            status = "incomplete"
        return PackageReadiness(
            status=status,
            cv_present=cv_ok,
            cover_letter_present=cl_ok,
            manifest_ref=f"package:{opportunity_id}",
        )

    def _observe_truth(
        self,
        opportunity_id: str,
        package: PackageReadiness,
    ) -> TruthReadiness:
        if package.status not in {"present", "stale"}:
            return TruthReadiness(status="absent")
        try:
            manifest = self._packages.get(opportunity_id, verify=False)
        except Exception:  # noqa: BLE001
            return TruthReadiness(status="absent")

        status_obj = evaluate_package_truth(
            manifest=manifest,
            profile=self._profile,
            store=self._truth_store,
            revalidate=False,
        )
        return _map_package_truth(status_obj)


def _map_package_truth(status: PackageTruthStatus) -> TruthReadiness:
    if not status.documents:
        return TruthReadiness(status="absent")

    refs = tuple(
        doc.report_id for doc in status.documents if doc.report_id is not None
    )
    if not refs:
        return TruthReadiness(status="absent")

    any_stale = any(not doc.fresh and doc.report_id for doc in status.documents)
    outcomes = {doc.outcome for doc in status.documents if doc.outcome is not None}
    blocking: list[str] = []
    for doc in status.documents:
        for msg in doc.messages:
            if "blocking" in msg.lower() or "stale" in msg.lower():
                blocking.append(msg[:120])

    owner_edited = any_stale  # hash mismatch ≡ owner-edited or regenerated bytes

    truth_status: TruthStatus
    if status.external_use_allowed:
        truth_status = "pass" if "warning" not in outcomes else "warning"
        owner_edited = False
    elif any_stale:
        truth_status = "stale"
    elif "fail" in outcomes:
        truth_status = "fail"
    elif "review_required" in outcomes:
        truth_status = "review_required"
    elif outcomes == {"warning"} or "warning" in outcomes:
        truth_status = "warning"
    else:
        # Reports present but not allowed — treat as review_required if unsure.
        truth_status = "review_required"

    if owner_edited and truth_status == "pass":
        truth_status = "stale"

    return TruthReadiness(
        status=truth_status,
        report_ref=",".join(refs),
        owner_edited_markdown_since_validation=owner_edited and truth_status != "pass",
        blocking_finding_codes=tuple(blocking[:8]),
    )


class StaticReadinessBuilder:
    """Test double: returns caller-supplied snapshots in sequence, then last."""

    def __init__(self, snapshots: list[ReadinessSnapshot]) -> None:
        if not snapshots:
            raise ValueError("StaticReadinessBuilder requires at least one snapshot")
        self._snapshots = list(snapshots)
        self._index = 0

    def build(
        self,
        opportunity_id: str,
        *,
        owner_approvals_present: bool,
        provider_available: bool = True,
        prior_agent_run_id: str | None = None,
        prior_agent_run_incomplete: bool = False,
        clarification_required: bool = False,
        clarification_message: str | None = None,
        contradictory_flags: tuple[str, ...] = (),
        observed_at: datetime | None = None,
    ) -> ReadinessSnapshot:
        base = self._snapshots[min(self._index, len(self._snapshots) - 1)]
        self._index += 1
        # Preserve corpus/fixture clarification and contradiction markers unless
        # the caller explicitly overlays them (runtime usually leaves defaults).
        overlay: dict[str, object] = {
            "opportunity_id": opportunity_id,
            "owner_approvals_present": owner_approvals_present,
            "provider_available": provider_available,
            "prior_agent_run_id": prior_agent_run_id,
            "prior_agent_run_incomplete": prior_agent_run_incomplete,
            "observed_at": observed_at or base.observed_at,
        }
        if clarification_required or clarification_message is not None:
            overlay["clarification_required"] = clarification_required
            overlay["clarification_message"] = clarification_message
        if contradictory_flags:
            overlay["contradictory_flags"] = contradictory_flags
        updated = base.model_copy(update=overlay)
        return updated.model_copy(
            update={"snapshot_hash": compute_snapshot_hash(updated)}
        )
