"""Per-request job_evidence item_index constraints (extraction boundary).

Domain ``JobEvidenceRef`` / ``validate_references`` stay fail-closed and unchanged.
This module only (1) injects per-collection JSON Schema enums for structured
output and (2) rejects invalid indexes during extraction coerce — no clamp,
modulo, remap, or fuzzy correction.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from career_intelligence.job_analysis.models import JobAnalysis

_LIST_SOURCE_LENGTHS = (
    ("technology", "technologies"),
    ("responsibility", "responsibilities"),
    ("experience_requirement", "experience_requirements"),
)


def job_analysis_list_lengths(job_analysis: JobAnalysis) -> dict[str, int]:
    """Map list job-evidence sources to their bound collection lengths."""
    return {
        "technology": len(job_analysis.technologies),
        "responsibility": len(job_analysis.responsibilities),
        "experience_requirement": len(job_analysis.experience_requirements),
    }


def valid_indexes_for_source(source: str, lengths: Mapping[str, int]) -> list[int]:
    """Exact valid item_index values for a list source (empty when length is 0)."""
    length = lengths.get(source, 0)
    if length <= 0:
        return []
    return list(range(length))


def validate_job_evidence_item_index(
    *,
    source: str,
    item_index: int | None,
    lengths: Mapping[str, int],
) -> None:
    """Raise ``ValueError`` unless ``item_index`` is exact for ``source``."""
    if source not in {"technology", "responsibility", "experience_requirement"}:
        if item_index is not None:
            raise ValueError(
                f"{source} job evidence must omit item_index "
                f"(got {item_index})"
            )
        return

    if item_index is None:
        raise ValueError(f"{source} job evidence requires item_index")
    if not isinstance(item_index, int) or isinstance(item_index, bool):
        raise ValueError(
            f"{source} item_index must be an integer, got {type(item_index).__name__}"
        )
    if item_index < 0:
        raise ValueError(
            f"{source} item_index {item_index} is out of range "
            f"(negative indexes are invalid)"
        )
    length = lengths.get(source, 0)
    if length <= 0:
        raise ValueError(
            f"{source} item_index {item_index} is out of range "
            f"for 0 {source} item(s)"
        )
    if item_index >= length:
        raise ValueError(
            f"{source} item_index {item_index} is out of range "
            f"for {length} {source} item(s)"
        )


def validate_job_evidence_indexes_in_payload(
    payload: Any,
    job_analysis: JobAnalysis,
) -> Any:
    """Walk extraction payload and reject any out-of-range list item_index."""
    lengths = job_analysis_list_lengths(job_analysis)
    _walk_validate(payload, lengths)
    return payload


def inject_job_evidence_item_index_enums(
    schema: dict[str, object],
    lengths: Mapping[str, int],
) -> dict[str, object]:
    """Constrain each list-source ``item_index`` to that collection's valid indexes.

    Uses separate ``$defs`` branches (technology / responsibility /
    experience_requirement) so a responsibility index cannot borrow a technology
    length. Empty collections get an unsatisfiable integer range (no silent
    acceptance).
    """
    patched = copy.deepcopy(schema)
    defs = patched.get("$defs")
    if not isinstance(defs, dict):
        defs = patched.get("definitions")
    if not isinstance(defs, dict):
        return patched

    for defn in defs.values():
        if not isinstance(defn, dict):
            continue
        props = defn.get("properties")
        if not isinstance(props, dict) or "source" not in props:
            continue
        if "item_index" not in props and "ref" in props:
            # Profile evidence ref — skip.
            continue
        source_prop = props.get("source")
        if not isinstance(source_prop, dict):
            continue
        list_source = _single_list_source(source_prop)
        if list_source is None:
            continue
        indexes = valid_indexes_for_source(list_source, lengths)
        item_schema = props.get("item_index")
        if not isinstance(item_schema, dict):
            continue
        if indexes:
            props["item_index"] = {
                **{
                    key: value
                    for key, value in item_schema.items()
                    if key not in {"enum", "minimum", "maximum", "exclusiveMaximum"}
                },
                "type": "integer",
                "enum": indexes,
            }
        else:
            # Unsatisfiable: no valid index exists for an empty collection.
            props["item_index"] = {
                "type": "integer",
                "minimum": 0,
                "maximum": -1,
            }
    return patched


def _single_list_source(source_prop: Mapping[str, object]) -> str | None:
    const = source_prop.get("const")
    if const in {"technology", "responsibility", "experience_requirement"}:
        return str(const)
    enum = source_prop.get("enum")
    if isinstance(enum, list) and len(enum) == 1:
        only = enum[0]
        if only in {"technology", "responsibility", "experience_requirement"}:
            return str(only)
    return None


def _walk_validate(node: Any, lengths: Mapping[str, int]) -> None:
    if isinstance(node, Mapping):
        evidence = node.get("job_evidence")
        if isinstance(evidence, list):
            for item in evidence:
                _validate_evidence_item(item, lengths)
        for value in node.values():
            _walk_validate(value, lengths)
        return
    if isinstance(node, list):
        for item in node:
            _walk_validate(item, lengths)
        return
    dump = getattr(node, "model_dump", None)
    if callable(dump):
        _walk_validate(dump(mode="python"), lengths)


def _validate_evidence_item(item: Any, lengths: Mapping[str, int]) -> None:
    if isinstance(item, Mapping):
        source = item.get("source")
        index = item.get("item_index")
    else:
        source = getattr(item, "source", None)
        index = getattr(item, "item_index", None)
    if not isinstance(source, str):
        return
    validate_job_evidence_item_index(
        source=source,
        item_index=index if index is None or isinstance(index, int) else index,
        lengths=lengths,
    )
