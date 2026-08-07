# FR-018 M2 — URL Acquisition + Thin Discovery Ingress

**Status:** **Complete (M2)** — **GO WITH REVISED SCOPE**  
**Date:** 2026-08-07  
**Phase:** Horizon 1B (lead FR)  
**Preceding:** [M0](fr018_m0_engineering_spike.md) (Accepted);
[M1](fr018_m1_discovery_contracts.md) (Accepted);
[ADR-010](../adr/010_opportunity_discovery_ingress.md)  
**Scope (M2):** Executable URL acquisition for owner-supplied SEEK / LinkedIn /
Indeed job URLs; thin `ThinDiscoveryIngress`; `cic opportunity discover`; offline
CI fixtures. **No** Playwright, email, feeds, scheduling, or Horizon 1A redesign.

---

## 1. Executive summary

M2 delivers the first executable FR-018 path:

```text
owner URL → UrlAcquisitionAdapter → ThinDiscoveryIngress
  → ApplicationWorkflowRunner → Opportunity / review (frozen 1A)
```

Offline fixture tests prove acquire → provenance → definite idempotency → runner
handoff. Live HTTP against a sample SEEK URL from this environment failed closed
with `network_failure` (no Playwright escalation). **Supported sources are
implemented and fixture-validated**; live board availability is **environment /
platform dependent** and must be validated by the owner on real public URLs.

**Verdict:** **GO WITH REVISED SCOPE** — ship SEEK/LinkedIn/Indeed *attempt*
path + clear unsupported/blocked failures; do not claim unconditional live
success for LinkedIn/Indeed (or SEEK) without owner live confirmation; no scrape
escalation.

---

## 2. Implementation summary

| Component | Location |
|-----------|----------|
| HTTP boundary | `discovery/http.py` (`HttpFetchClient`, `UrllibHttpClient`, `FakeHttpClient`) |
| URL classify / normalise | `discovery/url_support.py` |
| HTML extract (narrow) | `discovery/extract.py` |
| `UrlAcquisitionAdapter` / `StaticAcquisitionAdapter` | `discovery/url_adapter.py` |
| Definite idempotency | `discovery/idempotency.py` (reuses FR-009 `classify_pair`) |
| `ThinDiscoveryIngress` | `discovery/thin_ingress.py` |
| CLI | `cic opportunity discover <url>` |

---

## 3. Supported sources

| Platform | Locator requirement | Fixture validated | Live (this env) |
|----------|---------------------|-------------------|-----------------|
| SEEK | `/job/<id>` | Yes | Network failure on sample URL |
| LinkedIn | `/jobs/view/<id>` or `currentJobId` | Yes (HTML fixture) | Not live-tested here; often login-walled |
| Indeed | `jk=` job key | Yes (HTML fixture) | Not live-tested here |
| Other hosts | — | Fail `unsupported_source` | — |

Unsupported company career pages fail closed — no clever generic scrape.

---

## 4. URL fetch / extraction design

- Injectable `HttpFetchClient` — CI uses `FakeHttpClient` + saved HTML.
- Live: stdlib `UrllibHttpClient` (no new HTTP dependency).
- Timeout → `network_failure`; HTTP errors mapped; blocked/login-wall heuristics → fail closed.
- Extraction: strip script/style; prefer board description regions; min length; no LLM.

**WHY injectable fetch:** Offline deterministic CI.  
**Alternative:** Live HTTP in tests. **Rejected:** flaky / non-CI.  
**Principle:** Validate first; adapter isolation.  
**Interview:** Anti-corruption at the network boundary.

---

## 5. Provenance behaviour

After acquire, ingress calls `assert_url_acquisition_provenance` requiring
`source_kind=url`, `source_url`, `source_identifier`, `acquired_at`, non-empty
`raw_content`. Failures → `partial_metadata` / `malformed_content`.

---

## 6. Canonicalisation / identity

- `derive_source_facets` (existing) for platform / job id / canonical URL.
- Tracking query stripped for fetch (`utm_*`); job keys (`jk`, `currentJobId`) kept.
- `source_identifier` = canonical URL.

---

## 7. Idempotency / duplicates

- Pre-fetch skip when URL facets form a **definite** FR-009 match.
- Post-acquire definite check again.
- Fingerprint-only → **not** definite → does not auto-skip.
- Skip returns `matched_opportunity_id`; never merge/delete.
- `--force` bypasses skip.

---

## 8. DiscoveryIngress behaviour

`ThinDiscoveryIngress.discover`:

1. validate / classify supported URL  
2. optional definite skip  
3. `UrlAcquisitionAdapter.acquire`  
4. provenance assert  
5. optional definite skip  
6. `runner.start(StaticAcquisitionAdapter(result))` — **one** HTTP fetch  
7. return `DiscoveryOutcome` item  

No discovery catalogue writes.

---

## 9. CLI design

**Command:** `cic opportunity discover <url>`

**WHY under `opportunity`:** Discovery creates Opportunities into the existing SoT;
keeps one owner namespace vs a new `discovery` tree.  
**Alternative:** `cic discovery url`. **Rejected:** extra hierarchy for one verb.

Flags: `--dir`, `--checkpoint-dir`, `--profile`, `--force`, `--offline-fixtures`.

Outcomes printed: `ACQUIRED` / `SKIPPED_ALREADY_REPRESENTED` / `FAILED <kind>`.

---

## 10. Failure semantics

| Case | Kind / status |
|------|----------------|
| Invalid URL | `invalid_url` |
| Unsupported host / incomplete locator | `unsupported_source` |
| Timeout / DNS / HTTP | `network_failure` |
| Blocked / login wall | `adapter_failure` |
| Empty / short HTML | `malformed_content` |
| Missing provenance | `partial_metadata` |
| Definite duplicate | `skipped` + `definite_identity_match` |
| Runner exception | `runner_failure` |

---

## 11. Test results

| Suite | Result |
|-------|--------|
| `tests/unit/discovery/` | **35 passed** |
| FR-008 acquisition/runner/pre-review subset | **42 passed** |
| FR-009 detection subset | included in 42 |

Coverage includes: supported success, invalid/unsupported, timeout, HTTP error,
insufficient content, blocked page, provenance, platform ids, definite skip,
fingerprint non-skip, single fetch, runner failure, no discovery catalogue.

---

## 12. Manual validation

| Scenario | Result (engineering env) |
|----------|---------------------------|
| SEEK sample URL live fetch | **FAILED** `network_failure` (fail closed; no Playwright) |
| Fixture SEEK / LinkedIn / Indeed HTML | **PASS** (unit) |
| Duplicate URL twice (offline ingress) | **PASS** skip |
| Unsupported `example.com` | **PASS** `unsupported_source` |

**Owner action:** Run `cic opportunity discover <real-public-url>` on a reachable
network; if boards block plain HTTP, treat as known limitation — paste/export
remain available. Do **not** add Playwright in M3 solely to force those boards.

---

## 13. Horizon 1A regression

No changes to runner graph, Opportunity SoT semantics, FR-009 detection rules,
truth, agents, or submission. Orchestration regression subset green.

---

## 14. Risks / limitations

- Live board HTML often JS/login gated → ordinary HTTP may fail (documented).
- Title/company extraction is best-effort; warnings when missing.
- Linear Opportunity scan for idempotency (acceptable single-user).
- CLI live path still needs `OPENAI_API_KEY` unless `--offline-fixtures`.

---

## 15. Learning outcomes

| Decision | WHY | Rejected alternative | Principle | Interview |
|----------|-----|----------------------|-----------|-----------|
| Static adapter after acquire | One fetch | Double acquire in runner | Thin interfaces | Cache at boundary |
| FR-009 definite only | No false skip | Fingerprint auto-skip | Reuse SoT rules | Idempotency ≠ fuzzy dedupe |
| No Playwright in M2 | Lawful / maintainable | Scrape to “make tests pass” | No scrape theatre | Fail closed honestly |
| `opportunity discover` CLI | Fits SoT verb | New command tree | Scope control | Smallest owner UX |

---

## 16. Documentation updated

This report; changelog § 1.118; roadmap; functional spec; domain; testing;
implementation notes; phase history; AGENTS/README/repo guide; ADR-010 note.

---

## 17. M2 Go / No-Go

**GO WITH REVISED SCOPE**

- Proceed to M3 only for ops/batch polish **after** owner live validation on at
  least one real URL, **or** accept paste/export fallback when boards block HTTP.
- Do **not** introduce Playwright as the M3 default.
- Email/feeds remain later milestones.

**Post-M2 live validation (2026-08-07):** Complete —
[fr018_post_m2_live_url_validation.md](fr018_post_m2_live_url_validation.md).
SEEK **SUPPORTED**; LinkedIn partial; Indeed blocked. Recommend **M3 = A
(SEEK-first URL ops)**; M3 not started in that task.

---

## 18. Final repository status

| Item | Status |
|------|--------|
| Horizon 1A | Frozen |
| FR-018 M0–M1 | Accepted |
| FR-018 M2 | **Complete — GO WITH REVISED SCOPE** |
| M3 | Not started |

**M2 COMPLETE — GO WITH REVISED SCOPE**
