"""OAT-001 Phase 1 dry-run audit — read-only. Do not write Opportunity data."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from career_intelligence.opportunities.service import OpportunityService  # noqa: E402

JOBS = ROOT / "manual_validation" / "jobs"
OPP_ROOT = ROOT / "data" / "opportunities"
ART = OPP_ROOT / "artifacts"


def fingerprint_text(text: str) -> str:
    n = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(n.encode("utf-8")).hexdigest()


def load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_error": str(exc)}


def dig(obj, *paths):
    for path in paths:
        cur = obj
        ok = True
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                ok = False
                break
        if ok and isinstance(cur, str) and cur.strip():
            return cur
    return None


def posting_raw(posting: dict | None) -> str | None:
    if not isinstance(posting, dict) or "_error" in posting:
        return None
    for key in ("raw_text", "text", "description", "body", "content"):
        val = posting.get(key)
        if isinstance(val, str) and val.strip():
            return val
        if isinstance(val, dict):
            for k2 in ("raw_text", "text", "description"):
                if isinstance(val.get(k2), str) and val[k2].strip():
                    return val[k2]
    return None


def main() -> int:
    svc = OpportunityService.from_path(OPP_ROOT)
    opps = list(svc.list_opportunities())
    print(f"INDEX_COUNT={len(opps)}")
    print(f"ARTIFACT_DIRS={len(list(ART.iterdir())) if ART.exists() else 0}")

    job_files = sorted(JOBS.glob("*.txt"))
    print(f"JOB_TXT_COUNT={len(job_files)}")

    # Precompute job fingerprints and head text
    jobs = []
    for path in job_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        jobs.append(
            {
                "name": path.name,
                "path": str(path.relative_to(ROOT)),
                "fp": fingerprint_text(text),
                "size": len(text),
                "head": text[:240].replace("\n", " | "),
                "slug": path.stem,
            }
        )

    opp_rows = []
    for opp in opps:
        ident = opp.identity
        oid = opp.opportunity_id
        art_dir = ART / oid
        posting = load_json(art_dir / "posting.json")
        analysis = load_json(art_dir / "job_analysis.json")
        assessment = load_json(art_dir / "assessment.json")
        portfolio = load_json(art_dir / "portfolio_match.json")
        strategy = load_json(art_dir / "strategy.json")
        raw = posting_raw(posting)
        post_fp = fingerprint_text(raw) if raw else None

        posting_title = posting.get("title") if isinstance(posting, dict) else None
        posting_company = posting.get("company") if isinstance(posting, dict) else None
        analysis_title = dig(
            analysis or {},
            ("title",),
            ("job_title",),
            ("role_title",),
            ("role", "title"),
            ("extracted", "title"),
            ("identity", "title"),
            ("summary", "title"),
        )
        analysis_company = dig(
            analysis or {},
            ("company",),
            ("employer",),
            ("organisation",),
            ("organization",),
            ("extracted", "company"),
            ("identity", "company"),
            ("role", "company"),
        )

        # identity fingerprint field name varies by model version
        ident_dump = ident.model_dump(mode="json")
        ident_fp = (
            ident_dump.get("content_fingerprint")
            or ident_dump.get("fingerprint")
            or ident_dump.get("normalized_content_fingerprint")
        )

        decision = None
        if opp.decision is not None:
            decision = getattr(opp.decision, "decision", None) or str(opp.decision)

        pipeline = getattr(opp, "pipeline_status", None)
        if pipeline is None and hasattr(opp, "pipeline") and opp.pipeline is not None:
            pipeline = getattr(opp.pipeline, "status", None) or getattr(
                opp.pipeline, "current_status", None
            )

        source = ident_dump.get("source") or {}
        source_ref = None
        if isinstance(source, dict):
            source_ref = (
                source.get("source_ref")
                or source.get("path")
                or source.get("uri")
                or source.get("label")
            )

        opp_rows.append(
            {
                "opportunity_id": oid,
                "title": ident.title,
                "company": ident.company,
                "ident_fp": ident_fp,
                "post_fp": post_fp,
                "posting_title": posting_title,
                "posting_company": posting_company,
                "analysis_title": analysis_title,
                "analysis_company": analysis_company,
                "has_posting": isinstance(posting, dict) and "_error" not in posting,
                "has_analysis": isinstance(analysis, dict) and "_error" not in analysis,
                "has_assessment": isinstance(assessment, dict) and "_error" not in assessment,
                "has_portfolio": isinstance(portfolio, dict) and "_error" not in portfolio,
                "has_strategy": isinstance(strategy, dict) and "_error" not in strategy,
                "decision": decision,
                "pipeline": pipeline,
                "source": source,
                "source_ref": source_ref,
                "artifact_paths": opp.artifact_paths or {},
                "identity_dump": {
                    k: ident_dump.get(k)
                    for k in (
                        "title",
                        "company",
                        "source",
                        "content_fingerprint",
                        "fingerprint",
                        "platform",
                        "canonical_url",
                    )
                    if k in ident_dump
                },
            }
        )

    # Match jobs → opps
    # 1) exact posting fingerprint
    # 2) exact identity fingerprint
    # 3) source_ref path contains job filename
    # 4) slug token overlap with company/title
    mappings = []
    for job in jobs:
        matches = []
        for opp in opp_rows:
            reasons = []
            score = 0
            if opp["post_fp"] and opp["post_fp"] == job["fp"]:
                reasons.append("exact_posting_raw_fingerprint")
                score += 100
            if opp["ident_fp"] and opp["ident_fp"] == job["fp"]:
                reasons.append("exact_identity_fingerprint")
                score += 90
            ref = (opp["source_ref"] or "") if isinstance(opp["source_ref"], str) else ""
            src_s = json.dumps(opp["source"], default=str)
            if job["name"] in ref or job["name"] in src_s or job["slug"] in ref:
                reasons.append("source_ref_filename")
                score += 80
            # path-like
            if "manual_validation" in src_s and job["slug"] in src_s:
                reasons.append("source_contains_slug")
                score += 50
            if reasons:
                matches.append({"opp": opp, "score": score, "reasons": reasons})
        matches.sort(key=lambda m: -m["score"])
        mappings.append({"job": job, "matches": matches})

    out = {
        "totals": {
            "job_txt_files": len(jobs),
            "numbered_jobs": len([j for j in jobs if re.match(r"^\d{3}_", j["name"])]),
            "opportunities": len(opp_rows),
            "artifact_dirs": len(list(ART.iterdir())) if ART.exists() else 0,
        },
        "opportunities": [
            {
                "opportunity_id": r["opportunity_id"],
                "title": r["title"],
                "company": r["company"],
                "posting_title": r["posting_title"],
                "posting_company": r["posting_company"],
                "analysis_title": r["analysis_title"],
                "analysis_company": r["analysis_company"],
                "artefacts": {
                    "posting": r["has_posting"],
                    "analysis": r["has_analysis"],
                    "assessment": r["has_assessment"],
                    "portfolio": r["has_portfolio"],
                    "strategy": r["has_strategy"],
                },
                "decision": r["decision"],
                "pipeline": r["pipeline"],
                "source_ref": r["source_ref"],
                "source": r["source"],
                "ident_fp": r["ident_fp"],
                "post_fp": r["post_fp"],
                "needs_identity_backfill": r["title"] is None or r["company"] is None,
                "backfill_available_from_posting": bool(
                    (r["title"] is None and r["posting_title"])
                    or (r["company"] is None and r["posting_company"])
                ),
                "backfill_available_from_analysis": bool(
                    (r["title"] is None and r["analysis_title"])
                    or (r["company"] is None and r["analysis_company"])
                ),
            }
            for r in opp_rows
        ],
        "mappings": [
            {
                "job_file": m["job"]["name"],
                "job_path": m["job"]["path"],
                "job_fp": m["job"]["fp"],
                "job_head": m["job"]["head"],
                "match_count": len(m["matches"]),
                "matches": [
                    {
                        "opportunity_id": x["opp"]["opportunity_id"],
                        "score": x["score"],
                        "reasons": x["reasons"],
                        "title": x["opp"]["title"],
                        "company": x["opp"]["company"],
                    }
                    for x in m["matches"]
                ],
            }
            for m in mappings
        ],
    }

    out_path = ROOT / "data" / "_oat001_phase1_audit.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE={out_path}")

    # Console summary
    print("\n=== OPP SUMMARY ===")
    for r in out["opportunities"]:
        print(
            f"{r['opportunity_id']} title={r['title']!r} company={r['company']!r} "
            f"post=({r['posting_title']!r},{r['posting_company']!r}) "
            f"backfill_posting={r['backfill_available_from_posting']} "
            f"arts={r['artefacts']}"
        )

    print("\n=== JOB MAPPINGS ===")
    for m in out["mappings"]:
        if m["match_count"] == 0:
            status = "NO_MATCH"
        elif m["match_count"] == 1:
            status = "MATCH"
        else:
            status = "MULTI"
        ids = ",".join(x["opportunity_id"] for x in m["matches"])
        reasons = ";" .join(
            "+".join(x["reasons"]) for x in m["matches"]
        )
        print(f"{m['job_file']}: {status} -> {ids or '-'} ({reasons})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
