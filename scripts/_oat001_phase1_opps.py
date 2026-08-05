"""OAT-001 Phase 1 supplemental dry-run — opportunity timeline + raw_text identity hints."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "data" / "opportunities" / "index.yaml"
ART = ROOT / "data" / "opportunities" / "artifacts"
JOBS = ROOT / "manual_validation" / "jobs"
NOTES = JOBS / "manual_validation_notes.md"


def head_identity(raw: str) -> tuple[str | None, str | None]:
    """Best-effort display hint from posting raw_text first lines (report only)."""
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return None, None
    # Common SEEK: title then company
    title = lines[0] if lines else None
    company = None
    for ln in lines[1:6]:
        if ln.lower().startswith("view all"):
            continue
        if "logo for" in ln.lower():
            continue
        # Maincode style embeds company earlier
        if ln and len(ln) < 80 and not ln.lower().startswith("melbourne"):
            company = ln
            break
    return title, company


def main() -> int:
    opps = yaml.safe_load(INDEX.read_text(encoding="utf-8"))["opportunities"]
    rows = []
    for o in opps:
        ident = o["identity"]
        oid = ident["opportunity_id"]
        post = json.loads((ART / oid / "posting.json").read_text(encoding="utf-8"))
        raw = post.get("raw_text") or ""
        hint_t, hint_c = head_identity(raw)
        dec = o.get("decision")
        decision = dec.get("decision") if isinstance(dec, dict) else None
        rows.append(
            {
                "created_at": ident.get("created_at"),
                "opportunity_id": oid,
                "identity_title": ident.get("title"),
                "identity_company": ident.get("company"),
                "posting_title": post.get("title"),
                "posting_company": post.get("company"),
                "raw_hint_title": hint_t,
                "raw_hint_company": hint_c,
                "decision": decision,
                "source": ident.get("source"),
                "backfill_cli_can_fill": bool(
                    (ident.get("title") is None and post.get("title"))
                    or (ident.get("company") is None and post.get("company"))
                ),
            }
        )
    rows.sort(key=lambda r: r["created_at"] or "")
    out = ROOT / "data" / "_oat001_phase1_opps.json"
    out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE={out}")
    for r in rows:
        print(
            f"{r['created_at']} {r['opportunity_id']} "
            f"id=({r['identity_title']!r},{r['identity_company']!r}) "
            f"post=({r['posting_title']!r},{r['posting_company']!r}) "
            f"raw_hint=({r['raw_hint_title']!r},{r['raw_hint_company']!r}) "
            f"cli_backfill={r['backfill_cli_can_fill']} decision={r['decision']!r}"
        )

    # notes titles for missing jobs
    notes = NOTES.read_text(encoding="utf-8") if NOTES.is_file() else ""
    print("\n=== NOTES HEADERS ===")
    for m in re.finditer(r"^## Job (\d{3})[^\n]*\n(?:.*?\n)*?-\s*Title:\s*(.+)\n-\s*Company:\s*(.+)\n", notes, re.M):
        print(m.group(1), m.group(2).strip(), "|", m.group(3).strip())

    # 020 file head
    p020 = JOBS / "020_acenture_ai_engineer.txt"
    if p020.exists():
        print("\n020 head:", " ".join(p020.read_text(encoding="utf-8").split()[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
