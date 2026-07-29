"""Minimal ULID helper for workflow run ids — no extra dependency.

Same Crockford encoding as opportunity ids; kept local so orchestration does
not import opportunity package internals.
"""

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


def new_workflow_run_id() -> str:
    """Return a permanent ``wfr_<ULID>`` identifier."""
    return f"wfr_{generate_ulid()}"
