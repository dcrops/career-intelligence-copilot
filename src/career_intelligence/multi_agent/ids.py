"""ULID helpers for FR-016 orchestration ids."""

from __future__ import annotations

from career_intelligence.agent.ids import generate_ulid


def new_orchestration_run_id() -> str:
    """Return a permanent ``orr_<ULID>`` identifier."""
    return f"orr_{generate_ulid()}"


def new_handoff_id() -> str:
    """Return a permanent ``hof_<ULID>`` identifier."""
    return f"hof_{generate_ulid()}"


def new_orchestration_audit_event_id() -> str:
    """Return a permanent ``oae_<ULID>`` identifier."""
    return f"oae_{generate_ulid()}"


def new_operational_brief_id() -> str:
    """Return a permanent ``obr_<ULID>`` identifier."""
    return f"obr_{generate_ulid()}"
