"""DiscoveryIngress Protocol — thin coordination contract (FR-018 M1).

Implementations (later milestones) may only: resolve OpportunitySources,
instantiate AcquisitionAdapters, invoke ApplicationWorkflowRunner, and optionally
pre-check Opportunity identity for idempotent skip. No ranking, assessment,
persistence ownership, or duplicate-merge logic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import DiscoveryOutcome, DiscoveryRequest


@runtime_checkable
class DiscoveryIngress(Protocol):
    """Minimal public discovery coordination interface.

    M1 freezes the contract only. Executable ingress is a later milestone.
    """

    def discover(self, request: DiscoveryRequest) -> DiscoveryOutcome:
        """Resolve sources through adapters into the frozen Horizon 1A path.

        Must fail closed per item where possible; must not raise away a whole
        batch solely because one source failed unless the implementation
        documents that policy.
        """
        ...
