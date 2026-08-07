"""FR-018 post-M2 live URL validation — curl fetch + M2 extract path.

Production ``UrllibHttpClient`` fails SSL verify on this engineering host.
System ``curl.exe`` uses the Windows certificate store and can complete TLS.
This script does NOT redesign the adapter: it records (a) production client
failure and (b) board HTTP + extract outcomes via curl-fetched HTML, which is
what a fixed-TLS urllib client would see.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from career_intelligence.discovery import (
    DiscoveryUnsupportedSourceError,
    classify_supported_job_url,
)
from career_intelligence.discovery.extract import extract_job_content_from_html
from career_intelligence.discovery.http import HttpFetchError, UrllibHttpClient
from career_intelligence.opportunities.identity import derive_source_facets
from career_intelligence.orchestration.acquisition import AcquisitionError

ROOT = Path(__file__).resolve().parents[1]

URLS: list[tuple[str, str]] = [
    ("SEEK", "https://www.seek.com.au/job/93312273"),
    ("LINKEDIN", "https://www.linkedin.com/jobs/view/4429615445"),
    (
        "LINKEDIN_ALT",
        "https://www.linkedin.com/jobs/view/4436067784",
    ),
    ("INDEED", "https://au.indeed.com/viewjob?jk=6449f2b22e094d45"),
    ("CAREERS", "https://www.thoughtworks.com/careers/jobs/7920279"),
]

UA = "CareerIntelligenceCopilot/0.1 (+local owner job acquisition; not a crawler)"


def _body_signals(body: bytes) -> list[str]:
    low = body[:12000].lower()
    out: list[str] = []
    for token in (
        b"captcha",
        b"login",
        b"sign in",
        b"authwall",
        b"challenge",
        b"cf-mitigated",
        b"just a moment",
        b"robot",
        b"enable javascript",
        b"access denied",
        b"expired_jd_redirect",
        b"join now",
    ):
        if token in low:
            out.append(token.decode())
    return out


def curl_fetch(url: str, timeout: int = 35) -> tuple[int | None, str | None, bytes, str]:
    """Return (http_code, final_url_guess, body, error)."""
    with tempfile.TemporaryDirectory() as tmp:
        body_path = Path(tmp) / "body.bin"
        hdr_path = Path(tmp) / "hdr.txt"
        cmd = [
            "curl.exe",
            "-sL",
            "-A",
            UA,
            "--max-time",
            str(timeout),
            "-D",
            str(hdr_path),
            "-o",
            str(body_path),
            "-w",
            "%{http_code}\n%{url_effective}",
            url,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError as exc:
            return None, None, b"", f"curl_spawn_failed: {exc}"
        if proc.returncode != 0 and not body_path.exists():
            return None, None, b"", f"curl_exit_{proc.returncode}: {proc.stderr[:200]}"
        body = body_path.read_bytes() if body_path.exists() else b""
        lines = (proc.stdout or "").strip().splitlines()
        code: int | None = None
        final: str | None = None
        if lines:
            try:
                code = int(lines[0].strip())
            except ValueError:
                code = None
            if len(lines) > 1:
                final = lines[1].strip()
        return code, final, body, ""


def support_verdict(
    *,
    classified: bool,
    usable: bool,
    failure: str | None,
) -> str:
    if not classified:
        return "BLOCKED / UNSUPPORTED"
    if usable:
        return "SUPPORTED"
    if failure in {"unsupported_source"}:
        return "BLOCKED / UNSUPPORTED"
    # Classified board but not usable via lawful plain HTTP
    if failure in {
        "network_failure",
        "http_error",
        "blocked_response",
        "blocked_or_empty",
        "http_403",
        "http_401",
        "http_429",
        "login_wall",
        "cloudflare_challenge",
    }:
        return "BLOCKED / UNSUPPORTED"
    if classified and not usable:
        return "PARTIALLY_SUPPORTED"
    return "BLOCKED / UNSUPPORTED"


def run_row(label: str, url: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "label": label,
        "url": url,
        "source_classification": None,
        "platform": None,
        "platform_job_id": None,
        "canonical_url": None,
        "production_urllib": {},
        "curl_http": {},
        "usable_job_content": False,
        "title": None,
        "company": None,
        "raw_content_len": None,
        "provenance": {},
        "identity_facets": {},
        "opportunity_outcome": "not_persisted",
        "failure_category": None,
        "support_verdict": None,
        "notes": [],
    }

    # 1) Classification (existing M2 path)
    try:
        ref = classify_supported_job_url(url)
        row["source_classification"] = "allow-listed_board"
        row["platform"] = ref.platform
        row["platform_job_id"] = ref.platform_job_id
        row["canonical_url"] = ref.canonical_url
        row["provenance"] = {
            "source_kind": "url",
            "source_identifier": ref.source_identifier,
            "canonical_url": ref.canonical_url,
        }
        sk, pid, can = derive_source_facets(ref.canonical_url)
        row["identity_facets"] = {
            "source_kind": sk,
            "platform_job_id": pid,
            "canonical_url": can,
        }
    except DiscoveryUnsupportedSourceError as exc:
        row["source_classification"] = "unsupported_source"
        row["failure_category"] = "unsupported_source"
        row["opportunity_outcome"] = "failed"
        row["support_verdict"] = "BLOCKED / UNSUPPORTED"
        row["notes"].append(str(exc))
        # Still record curl for optional careers visibility
        code, final, body, err = curl_fetch(url)
        row["curl_http"] = {
            "status": code,
            "final_url": final,
            "bytes": len(body),
            "signals": _body_signals(body) if body else [],
            "error": err or None,
        }
        return row
    except Exception as exc:  # noqa: BLE001
        row["source_classification"] = "classify_error"
        row["failure_category"] = type(exc).__name__
        row["opportunity_outcome"] = "failed"
        row["support_verdict"] = "BLOCKED / UNSUPPORTED"
        row["notes"].append(str(exc))
        return row

    # 2) Production UrllibHttpClient (exact M2 live path)
    try:
        resp = UrllibHttpClient().get(url, timeout_seconds=25.0)
        row["production_urllib"] = {
            "ok": True,
            "status": resp.status_code,
            "bytes": len(resp.body),
            "final_url": resp.url,
        }
    except HttpFetchError as exc:
        row["production_urllib"] = {
            "ok": False,
            "kind": exc.kind,
            "status": exc.status_code,
            "detail": (exc.detail or "")[:240],
        }

    # 3) curl.exe fetch (system TLS) — board reality under plain HTTP UA
    code, final, body, err = curl_fetch(url)
    signals = _body_signals(body) if body else []
    row["curl_http"] = {
        "status": code,
        "final_url": final,
        "bytes": len(body),
        "signals": signals,
        "error": err or None,
        "content_type_guess": (
            "html" if b"<html" in body[:500].lower() or b"<!doctype" in body[:200].lower() else "unknown"
        ),
    }

    if err and not body:
        row["failure_category"] = "network_failure"
        row["opportunity_outcome"] = "failed"
        row["support_verdict"] = support_verdict(
            classified=True, usable=False, failure="network_failure"
        )
        row["notes"].append(err)
        return row

    if code is not None and code >= 400:
        failure = f"http_{code}"
        if code == 403 and ("challenge" in signals or "cf-mitigated" in signals or b"cf-" in body[:2000].lower()):
            failure = "cloudflare_challenge"
        row["failure_category"] = failure
        row["opportunity_outcome"] = "failed"
        row["support_verdict"] = support_verdict(
            classified=True, usable=False, failure=failure
        )
        return row

    # 4) Existing extractor (same as UrlAcquisitionAdapter)
    try:
        html = body.decode("utf-8", errors="replace")
        extracted = extract_job_content_from_html(html, platform=row["platform"])
        raw = extracted.raw_text or ""
        row["title"] = extracted.title
        row["company"] = extracted.company
        row["raw_content_len"] = len(raw)

        # Post-extract quality gate for live validation (not an adapter redesign):
        # LinkedIn often 200-redirects expired jobs to search/list pages that still
        # yield long HTML text — that must not count as a usable job advertisement.
        quality_fail = _live_quality_failure(
            platform=str(row["platform"]),
            title=extracted.title,
            raw=raw,
            final_url=final,
            signals=signals,
        )
        usable = len(raw) >= 200 and quality_fail is None
        row["usable_job_content"] = usable
        if usable:
            row["opportunity_outcome"] = "would_create_if_persisted"
            row["failure_category"] = None
            row["support_verdict"] = "SUPPORTED"
        else:
            row["opportunity_outcome"] = "failed"
            row["failure_category"] = quality_fail or "blocked_or_empty"
            row["support_verdict"] = (
                "PARTIALLY_SUPPORTED"
                if code == 200 and quality_fail
                else support_verdict(
                    classified=True, usable=False, failure=row["failure_category"]
                )
            )
            if quality_fail:
                row["notes"].append(
                    "HTTP/extract produced text, but live quality gate rejected it "
                    f"as non-job content ({quality_fail})"
                )
            else:
                row["notes"].append(
                    "HTTP succeeded but extracted content too thin for usable job ad"
                )
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", None) or str(exc)
        failure = str(detail) if detail else type(exc).__name__
        if "blocked" in failure.lower() or "login" in str(exc).lower():
            failure = "blocked_response"
        if any(s in signals for s in ("authwall", "sign in", "login", "join now")):
            failure = "login_wall"
        row["failure_category"] = failure
        row["opportunity_outcome"] = "failed"
        row["notes"].append(str(exc)[:300])
        row["support_verdict"] = support_verdict(
            classified=True, usable=False, failure=failure
        )

    return row


def _live_quality_failure(
    *,
    platform: str,
    title: str | None,
    raw: str,
    final_url: str | None,
    signals: list[str],
) -> str | None:
    """Return failure category if extracted text is not a real single job ad."""
    final_l = (final_url or "").lower()
    title_l = (title or "").lower()
    if platform == "linkedin":
        if "expired_jd_redirect" in final_l or "expired_jd_redirect" in signals:
            return "linkedin_expired_or_search_redirect"
        if re.search(r"\d[\d,]+\+?\s+\S+\s+jobs?\b", title or "", flags=re.I):
            return "linkedin_listing_page_not_job"
        if "/jobs/view/" not in final_l and "currentjobid=" not in final_l:
            return "linkedin_not_job_view"
        if any(s in signals for s in ("authwall", "sign in", "login")) and len(raw) < 1500:
            return "login_wall"
    if platform == "indeed" and any(
        s in signals for s in ("captcha", "challenge", "cf-mitigated", "just a moment")
    ):
        return "cloudflare_challenge"
    return None


def main() -> int:
    stamped = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = [run_row(label, url) for label, url in URLS]

    meaningful = [
        r
        for r in rows
        if r["label"].startswith(("SEEK", "LINKEDIN", "INDEED"))
        and r["support_verdict"] == "SUPPORTED"
    ]
    hypothesis = bool(meaningful)
    recommendation = (
        "A. M3 = operationalise URL acquisition"
        if hypothesis
        else "B. M3 = email-alert acquisition"
    )

    # Summarise production urllib SSL issue
    ssl_failures = [
        r["label"]
        for r in rows
        if r.get("production_urllib", {}).get("ok") is False
        and "CERTIFICATE" in str(r.get("production_urllib", {}).get("detail", ""))
    ]

    payload = {
        "generated_at_utc": stamped,
        "purpose": "FR-018 post-M2 live URL validation (no M3)",
        "method": (
            "classify via M2 classify_supported_job_url; "
            "record UrllibHttpClient outcome; "
            "fetch HTML via curl.exe (system TLS); "
            "extract via extract_job_content_from_html (same as UrlAcquisitionAdapter). "
            "No Opportunity persistence. No Playwright."
        ),
        "ssl_environment": {
            "urllib_ssl_broken_for": ssl_failures,
            "note": (
                "Python urllib SSL verify fails on this host for major boards "
                "(CERTIFICATE_VERIFY_FAILED). curl.exe succeeds TLS. Board "
                "accessibility conclusions use curl + extract, not a redesigned adapter."
            ),
        },
        "urls": [{"label": n, "url": u} for n, u in URLS],
        "results": rows,
        "url_first_hypothesis_survived": hypothesis,
        "recommended_m3_direction": recommendation,
        "meaningful_supported_sources": [r["label"] for r in meaningful],
    }

    out = ROOT / "docs" / "eval" / f"fr018_post_m2_live_url_validation_{stamped}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
