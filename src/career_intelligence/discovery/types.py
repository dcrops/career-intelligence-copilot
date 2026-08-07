"""Literal types for FR-018 discovery contracts."""

from __future__ import annotations

from typing import Literal, get_args

# URL (M2–M3) + email job alerts (M4). Other AcquisitionSourceKind values remain
# reserved on the FR-008 adapter boundary for later milestones.
DiscoverySourceKind = Literal["url", "email"]

DISCOVERY_SOURCE_KINDS: tuple[DiscoverySourceKind, ...] = get_args(DiscoverySourceKind)
