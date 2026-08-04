"""Narrow canonicalisation of profile evidence refs at the extraction boundary.

Domain ``ProfileEvidenceRef`` stays fail-closed (no silent repair). This module
only peels recognised surrounding/trailing serialisation punctuation and then
requires an exact catalogue-token match. No fuzzy matching. Unknown or
ambiguous results stay rejected.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

# Serialisation junk the model sometimes glues onto catalogue tokens when the
# structured-output schema leaves ``ref`` as a free-form string.
_TRAILING_SERIALIZATION = frozenset(".,;:!?)]}\"'\n\r\t ")
_LEADING_SERIALIZATION = frozenset("{[(\"'`")


def canonicalize_profile_evidence_ref(raw: str, catalogue: frozenset[str]) -> str:
    """Return the exact catalogue token for ``raw``, or raise ``ValueError``.

    Exact catalogue hits pass through unchanged. Otherwise peel only recognised
    leading/trailing serialisation characters and require exactly one catalogue
    match among the peeled candidates.
    """
    if not isinstance(raw, str):
        raise ValueError(f"profile evidence ref must be a string, got {type(raw).__name__}")

    if raw in catalogue:
        return raw

    matches = [
        candidate
        for candidate in _peel_candidates(raw)
        if candidate in catalogue
    ]
    unique = list(dict.fromkeys(matches))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        raise ValueError(
            "ambiguous profile evidence ref after canonicalisation "
            f"(got {raw!r}; matches {unique!r})"
        )
    raise ValueError(
        "unknown profile evidence ref after canonicalisation "
        f"(got {raw!r})"
    )


def canonicalize_profile_evidence_refs_in_payload(
    payload: Any,
    catalogue: Sequence[str] | frozenset[str],
) -> Any:
    """Deep-copy walk: rewrite ``profile_evidence[].ref`` via catalogue rules."""
    allowed = frozenset(catalogue)
    return _rewrite(payload, allowed)


def _peel_candidates(raw: str) -> list[str]:
    """Generate candidates by peeling recognised serialisation punctuation only."""
    candidates: list[str] = [raw]
    trailing_peeled = raw
    while trailing_peeled and trailing_peeled[-1] in _TRAILING_SERIALIZATION:
        trailing_peeled = trailing_peeled[:-1]
        candidates.append(trailing_peeled)

    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(candidate)
        leading_peeled = candidate
        while leading_peeled and leading_peeled[0] in _LEADING_SERIALIZATION:
            leading_peeled = leading_peeled[1:]
            expanded.append(leading_peeled)
    return list(dict.fromkeys(expanded))


def _rewrite(node: Any, catalogue: frozenset[str]) -> Any:
    if isinstance(node, Mapping):
        data: dict[str, Any] = {
            key: _rewrite(value, catalogue) for key, value in node.items()
        }
        evidence = data.get("profile_evidence")
        if isinstance(evidence, list):
            data["profile_evidence"] = [
                _rewrite_evidence_item(item, catalogue) for item in evidence
            ]
        return data
    if isinstance(node, list):
        return [_rewrite(item, catalogue) for item in node]
    return node


def _rewrite_evidence_item(item: Any, catalogue: frozenset[str]) -> Any:
    if isinstance(item, MutableMapping) or isinstance(item, Mapping):
        rewritten = dict(item)
        if "ref" in rewritten and rewritten["ref"] is not None:
            rewritten["ref"] = canonicalize_profile_evidence_ref(
                str(rewritten["ref"]), catalogue
            )
        return rewritten
    ref = getattr(item, "ref", None)
    if ref is None:
        return item
    dump = item.model_dump(mode="python") if hasattr(item, "model_dump") else None
    if isinstance(dump, dict):
        dump["ref"] = canonicalize_profile_evidence_ref(str(ref), catalogue)
        return dump
    return item
