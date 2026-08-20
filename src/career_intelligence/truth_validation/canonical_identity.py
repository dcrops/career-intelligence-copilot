"""FR-014 reuse of M2 canonical capability *identity* only.

This module imports ``resolve_identity`` and ``aliases_for_identity``.
It must not import ``classify_requirement``, RELATED maps, or positioning
permission (``may_claim_requested``). Identity equivalence is not claim
permission: AWS is not AWS Bedrock DIRECT.
"""

from __future__ import annotations

from career_intelligence.document_positioning.catalogue import (
    aliases_for_identity,
    resolve_identity,
)
from career_intelligence.truth_validation.aliases import alias_keys_for
from career_intelligence.truth_validation.normalise import normalise_object_key


def canonical_identity(label: str) -> str | None:
    """Return the shared M2 identity for ``label``, or None if unknown."""
    return resolve_identity(label)


def identity_match_keys(label: str) -> frozenset[str]:
    """Object keys that are the same canonical identity as ``label``.

    Includes FR-014's existing tiny alias groups (js/ts/…) plus M2 identity
    aliases when ``label`` resolves. RELATED identities are not included.
    """
    keys = {normalise_object_key(label)} | set(alias_keys_for(label))
    identity = resolve_identity(label)
    if identity is None:
        return frozenset(key for key in keys if key)
    keys.add(normalise_object_key(identity))
    for alias in aliases_for_identity(identity):
        keys.add(normalise_object_key(alias))
    return frozenset(key for key in keys if key)


def scan_labels_for_identity(label: str) -> tuple[str, ...]:
    """Surface phrases FR-014 should scan for the same identity as ``label``."""
    identity = resolve_identity(label)
    if identity is None:
        return (label,) if label.strip() else ()
    phrases = [label, *aliases_for_identity(identity)]
    seen: set[str] = set()
    ordered: list[str] = []
    for phrase in phrases:
        key = normalise_object_key(phrase)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(phrase)
    return tuple(ordered)
