#!/usr/bin/env python3
"""Build Engineering Learning Academy Masterclass source packages.

Copies or extracts authoritative repository documentation into
``docs/masterclass/FRnnn/sources/`` as generated snapshots.

The repository docs remain the source of truth. Snapshots are regenerable
mirrors for single-folder Academy attachment — do not edit them by hand.

Usage:
  python scripts/build_masterclass_package.py FR016
  python scripts/build_masterclass_package.py --all
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FullCopy:
    repo_path: str
    package_path: str


@dataclass(frozen=True)
class SectionExtract:
    repo_path: str
    package_path: str
    start_heading: str
    end_heading: str | None = None  # exclusive; None = EOF


@dataclass(frozen=True)
class PackageSpec:
    fr_id: str  # e.g. FR016
    sources: tuple[FullCopy | SectionExtract, ...]


# Packaging recipes — add a PackageSpec when a frozen FR adopts this pattern.
PACKAGES: dict[str, PackageSpec] = {
    "FR016": PackageSpec(
        fr_id="FR016",
        sources=(
            FullCopy(
                "docs/eval/fr016_multi_agent_orchestration.md",
                "sources/acceptance.md",
            ),
            FullCopy(
                "docs/adr/008_multi_agent_orchestration.md",
                "sources/adr.md",
            ),
            SectionExtract(
                "docs/04_functional_specification.md",
                "sources/functional_specification.md",
                start_heading="## FR-016 Multi-Agent Orchestration",
                end_heading="## FR-017 Agent Evaluation & Observability",
            ),
            SectionExtract(
                "docs/06_domain_model.md",
                "sources/domain_model.md",
                start_heading="### Multi-Agent Orchestration (FR-016)",
                end_heading="## Entity Relationships",
            ),
            SectionExtract(
                "docs/08_implementation_notes.md",
                "sources/implementation_notes.md",
                start_heading="## FR-016 M1 — Multi-agent orchestration contracts",
                end_heading=None,
            ),
            SectionExtract(
                "docs/07_testing_strategy.md",
                "sources/testing_strategy.md",
                start_heading="### FR-016 coverage (M1–M4 — frozen)",
                end_heading="**Spike rule:**",
            ),
            FullCopy(
                "docs/eval/fr016_m0_engineering_spike.md",
                "sources/optional/m0_spike.md",
            ),
            FullCopy(
                "docs/eval/fr016_m1_orchestration_contracts.md",
                "sources/optional/m1.md",
            ),
            FullCopy(
                "docs/eval/fr016_m2_supervisor_runtime.md",
                "sources/optional/m2.md",
            ),
            FullCopy(
                "docs/eval/fr016_m3_owner_cli.md",
                "sources/optional/m3.md",
            ),
            FullCopy(
                "docs/eval/fr016_m4_evaluation.md",
                "sources/optional/m4.md",
            ),
        ),
    ),
}


def _banner(repo_rel: str, mode: str) -> str:
    return (
        "<!--\n"
        "GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.\n"
        f"Authoritative source: {repo_rel}\n"
        f"Mode: {mode}\n"
        "Regenerate: python scripts/build_masterclass_package.py "
        f"<FR_ID>\n"
        "Repository documentation remains the source of truth.\n"
        "-->\n\n"
    )


def _extract_section(
    text: str,
    *,
    start_heading: str,
    end_heading: str | None,
) -> str:
    start = text.find(start_heading)
    if start < 0:
        raise ValueError(f"start heading not found: {start_heading!r}")
    if end_heading is None:
        body = text[start:]
    else:
        end = text.find(end_heading, start + len(start_heading))
        if end < 0:
            raise ValueError(f"end heading not found: {end_heading!r}")
        body = text[start:end]
    return body.rstrip() + "\n"


def build_package(spec: PackageSpec) -> list[Path]:
    package_root = ROOT / "docs" / "masterclass" / spec.fr_id
    if not package_root.is_dir():
        raise FileNotFoundError(f"package folder missing: {package_root}")

    written: list[Path] = []
    for item in spec.sources:
        src = ROOT / item.repo_path
        if not src.is_file():
            raise FileNotFoundError(f"authoritative source missing: {src}")
        dest = package_root / item.package_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_text(encoding="utf-8")
        if isinstance(item, FullCopy):
            body = raw if raw.endswith("\n") else raw + "\n"
            mode = "full-file snapshot"
        else:
            body = _extract_section(
                raw,
                start_heading=item.start_heading,
                end_heading=item.end_heading,
            )
            mode = (
                f"section snapshot ({item.start_heading!r}"
                f" → {item.end_heading!r})"
            )
        dest.write_text(_banner(item.repo_path, mode) + body, encoding="utf-8")
        written.append(dest)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fr_id",
        nargs="?",
        help="Package id, e.g. FR016",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build every registered package",
    )
    args = parser.parse_args(argv)

    if args.all:
        targets = list(PACKAGES.values())
    elif args.fr_id:
        key = args.fr_id.strip().upper().replace("-", "").replace("_", "")
        if not key.startswith("FR"):
            key = f"FR{key}"
        # Normalise FR16 -> FR016
        match = re.fullmatch(r"FR0*(\d+)", key)
        if match:
            key = f"FR{int(match.group(1)):03d}"
        if key not in PACKAGES:
            print(f"Unknown package {key!r}. Registered: {sorted(PACKAGES)}", file=sys.stderr)
            return 1
        targets = [PACKAGES[key]]
    else:
        parser.error("provide FR id or --all")

    for spec in targets:
        paths = build_package(spec)
        print(f"{spec.fr_id}: wrote {len(paths)} snapshot(s)")
        for path in paths:
            print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
