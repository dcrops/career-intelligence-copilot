"""Analyse preferred strategy JSON exports for calibration review.

Does not import or modify production src.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
LIVE = OUT / "live"

# Stem labels in requested order. Prefer live/<match> else outputs/<match>.
STEM_SPECS: list[tuple[str, str]] = [
    # (label, glob/prefix matcher)
    ("014", "014_"),
    ("015", "015_"),
    ("017", "017_"),
    ("013", "013_"),
    ("001", "001_strong_ai_engineer.json"),  # exact preferred base name
    ("002_bluefin", "002_bluefin_"),
    ("004", "004_associate_ai_product_manager.json"),
    ("006", "006_senior_ai_engineer_kogan.json"),
    ("008", "008_"),
    ("009", "009_forever_new_senior_ai_automation_engineer_digital.json"),
    ("010", "010_"),
    ("011", "011_"),
    ("012", "012_"),
    ("007", "007_"),
    ("005", "005_"),
    ("001_after_fix", "001_strong_ai_engineer_after_fix.json"),
    ("006_after_fix", "006_senior_ai_engineer_kogan_after_fix.json"),
    ("009_after_calibration", "009_forever_new_senior_ai_automation_engineer_digital_after_calibration.json"),
    ("job", "job.json"),
]

COMMERCIAL_NOTE_TERMS = (
    "data engineer",
    "commercial ai",
    "independent",
    "employment",
)
TECHNICAL_NOTE_TERMS = ("ai", "portfolio", "llm")


def _is_after_stem(label: str) -> bool:
    return "after" in label.lower()


def resolve_path(label: str, matcher: str) -> Path | None:
    """Prefer live/ if a matching file exists, else outputs/ root."""

    def candidates(base: Path) -> list[Path]:
        if not base.is_dir():
            return []
        if matcher.endswith(".json"):
            p = base / matcher
            return [p] if p.is_file() else []
        # prefix match; exclude after_* variants when resolving a non-after stem
        hits = sorted(base.glob(f"{matcher}*"))
        if not _is_after_stem(label):
            hits = [
                h
                for h in hits
                if "after_" not in h.name.lower() and h.suffix == ".json"
            ]
        else:
            hits = [h for h in hits if h.suffix == ".json"]
        # For exact-ish prefixes like 014_, pick the single primary file
        if matcher.endswith("_") and not matcher.endswith(".json"):
            # Prefer exact stem file without after
            primary = [h for h in hits if h.name.startswith(matcher)]
            return primary[:1] if primary else []
        return hits[:1]

    live_hits = candidates(LIVE)
    if live_hits:
        return live_hits[0]
    root_hits = candidates(OUT)
    return root_hits[0] if root_hits else None


def one_line(text: str | None, n: int = 120) -> str:
    if not text:
        return ""
    s = re.sub(r"\s+", " ", str(text)).strip()
    return s if len(s) <= n else s[: n - 1] + "..."


def mention_flags(texts: list[str], terms: tuple[str, ...]) -> list[str]:
    blob = " ".join(texts).lower()
    return [t for t in terms if t in blob]


def role_family_value(ja: dict) -> str:
    rf = ja.get("role_family")
    if isinstance(rf, dict):
        return str(rf.get("family") or "")
    return str(rf or "")


def fit_block(name: str, fit: dict | None, note_terms: tuple[str, ...]) -> None:
    fit = fit or {}
    judgment = fit.get("judgment")
    summary = one_line(fit.get("summary"), 140)
    print(f"  {name}: judgment={judgment}")
    print(f"    summary: {summary}")
    findings = fit.get("findings") or []
    texts: list[str] = [str(fit.get("summary") or "")]
    if findings:
        print(f"    findings ({len(findings)}):")
        for f in findings:
            kind = f.get("kind")
            fsum = one_line(f.get("summary"), 80)
            print(f"      - kind={kind} | {fsum}")
            texts.append(str(f.get("summary") or ""))
            texts.append(str(f.get("detail") or ""))
    else:
        print("    findings: (none)")
    hits = mention_flags(texts, note_terms)
    if hits:
        print(f"    note mentions: {', '.join(hits)}")
    else:
        print("    note mentions: (none of watched terms)")


def portfolio_block(pm: dict | None) -> list[str]:
    """Print ranked projects; return ordered project_ids."""
    pm = pm or {}
    ranked = pm.get("ranked_projects") or pm.get("matched_projects") or []
    ids: list[str] = []
    if not ranked:
        print("  portfolio_match: (no ranked/matched projects)")
        return ids
    print(f"  portfolio_match ranked ({len(ranked)}):")
    for item in ranked:
        pid = item.get("project_id") or item.get("id") or "?"
        rank = item.get("rank")
        ids.append(str(pid))
        rationale = one_line(item.get("rationale") or item.get("selection_reason"), 100)
        factors = item.get("factors") or item.get("selection_reasons") or []
        factor_kinds = []
        for fac in factors[:6]:
            if isinstance(fac, dict):
                factor_kinds.append(str(fac.get("kind") or fac.get("summary") or "?")[:40])
            else:
                factor_kinds.append(one_line(str(fac), 40))
        extra = ""
        if factor_kinds:
            extra = " factors=[" + ", ".join(factor_kinds)
            if len(factors) > 6:
                extra += f", ...+{len(factors) - 6}"
            extra += "]"
        print(f"    #{rank} {pid}: {rationale}{extra}")
    return ids


def strategy_extras(st: dict | None) -> None:
    st = st or {}
    actions = st.get("next_actions") or []
    kinds = [str(a.get("kind") or "?") for a in actions if isinstance(a, dict)]
    print(f"  strategy.next_actions kinds: {kinds if kinds else '(none)'}")
    emph = st.get("portfolio_emphasis") or []
    if isinstance(emph, list):
        pids = []
        for e in emph:
            if isinstance(e, dict):
                pids.append(str(e.get("project_id") or "?"))
            else:
                pids.append(str(e))
        print(f"  strategy.portfolio_emphasis project_ids: {pids if pids else '(none)'}")
    elif isinstance(emph, dict):
        print(f"  strategy.portfolio_emphasis: {one_line(json.dumps(emph), 120)}")
    else:
        print(f"  strategy.portfolio_emphasis: {emph!r}")


def analyse_one(label: str, path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    posting = data.get("posting") or {}
    ja = data.get("job_analysis") or {}
    oa = data.get("opportunity_assessment") or {}
    pm = data.get("portfolio_match") or {}
    st = data.get("application_strategy") or {}

    company = posting.get("company") or (ja.get("posting") or {}).get("company")
    title = posting.get("title") or (ja.get("posting") or {}).get("title")
    tier = st.get("application_tier")
    posture = st.get("pursuit_posture")
    effort = st.get("effort_level")
    family = role_family_value(ja)

    src = "live" if LIVE in path.parents or path.parent == LIVE else "outputs"
    print("=" * 72)
    print(f"stem={label}  source={src}  file={path.name}")
    print(f"  company={company}  title={title}")
    print(f"  tier={tier}  posture={posture}  effort={effort}  role_family={family}")

    tech = oa.get("technical_fit") or {}
    comm = oa.get("commercial_fit") or {}
    port = oa.get("portfolio_fit") or {}

    print(f"  technical_fit: {tech.get('judgment')} | {one_line(tech.get('summary'), 140)}")
    print(f"  commercial_fit: {comm.get('judgment')} | {one_line(comm.get('summary'), 140)}")
    print(f"  portfolio_fit: {port.get('judgment')} | {one_line(port.get('summary'), 140)}")

    fit_block("commercial_fit detail", comm, COMMERCIAL_NOTE_TERMS)
    fit_block("technical_fit detail", tech, TECHNICAL_NOTE_TERMS)
    ranked_ids = portfolio_block(pm)
    strategy_extras(st)
    print()

    return {
        "label": label,
        "is_after": _is_after_stem(label),
        "tier": tier,
        "commercial_judgment": comm.get("judgment"),
        "ranked_ids": ranked_ids,
    }


def print_counts(title: str, counter: Counter) -> None:
    print(title)
    if not counter:
        print("  (empty)")
        return
    width = max(len(str(k)) for k in counter) if counter else 10
    for key, n in counter.most_common():
        print(f"  {str(key):<{width}}  {n}")


def main() -> None:
    print("Preferred strategy calibration review")
    print(f"outputs root: {OUT}")
    print(f"live prefer:  {LIVE}")
    print()

    results: list[dict] = []
    missing: list[str] = []

    for label, matcher in STEM_SPECS:
        path = resolve_path(label, matcher)
        if path is None:
            missing.append(label)
            print("=" * 72)
            print(f"stem={label}  MISSING (no live/ or outputs/ match for {matcher!r})")
            print()
            continue
        results.append(analyse_one(label, path))

    # Aggregates over preferred non-after jobs only
    preferred = [r for r in results if not r["is_after"]]
    top1: Counter = Counter()
    top3: Counter = Counter()
    commercial: Counter = Counter()
    tiers: Counter = Counter()

    for r in preferred:
        ids = r["ranked_ids"]
        if ids:
            top1[ids[0]] += 1
            for pid in ids[:3]:
                top3[pid] += 1
        commercial[str(r["commercial_judgment"])] += 1
        tiers[str(r["tier"])] += 1

    print("=" * 72)
    print("AGGREGATES (preferred non-after jobs only)")
    print(f"n_jobs={len(preferred)}  (excluded after_*={sum(1 for r in results if r['is_after'])})")
    print()
    print_counts("Project appearances in TOP-1:", top1)
    print()
    print_counts("Project appearances in TOP-3:", top3)
    print()
    print_counts("Commercial judgment counts:", commercial)
    print()
    print_counts("Tier counts:", tiers)

    if missing:
        print()
        print("MISSING STEMS:", ", ".join(missing))


if __name__ == "__main__":
    main()
