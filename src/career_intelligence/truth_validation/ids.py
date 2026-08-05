"""Minimal ULID helper for truth-validation ids — no extra dependency."""

from __future__ import annotations

import os
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_ulid(*, timestamp_ms: int | None = None) -> str:
    """Return a new 26-character ULID string."""
    ms = int(time.time() * 1000) if timestamp_ms is None else timestamp_ms
    if ms < 0 or ms >= 2**48:
        raise ValueError("timestamp_ms must fit in 48 bits")

    randomness = int.from_bytes(os.urandom(10), "big")
    value = (ms << 80) | randomness
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_truth_report_id() -> str:
    """Return a permanent ``trp_<ULID>`` identifier."""
    return f"trp_{generate_ulid()}"


def new_truth_finding_id() -> str:
    """Return a permanent ``tfd_<ULID>`` identifier."""
    return f"tfd_{generate_ulid()}"


def new_claim_id() -> str:
    """Return a permanent ``tcl_<ULID>`` identifier."""
    return f"tcl_{generate_ulid()}"


def new_catalogue_entry_id() -> str:
    """Return a permanent ``tee_<ULID>`` identifier."""
    return f"tee_{generate_ulid()}"
