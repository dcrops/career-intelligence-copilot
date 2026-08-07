# FR-018 M3 — Production Hardening & Source Expansion

**Status:** **Complete (M3)** — **GO WITH REVISED SCOPE**  
**Date:** 2026-08-07  
**Phase:** Horizon 1B (lead FR)  
**Preceding:** [M0](fr018_m0_engineering_spike.md), [M1](fr018_m1_discovery_contracts.md),
[M2](fr018_m2_url_discovery_ingress.md),
[post-M2 live validation](fr018_post_m2_live_url_validation.md)  
**ADR:** [ADR-010](../adr/010_opportunity_discovery_ingress.md)

---

## 1. Executive summary

M3 production-hardens the M2 URL path without scrape theatre.

| Area | Outcome |
|------|---------|
| SEEK | **Production ready** — live `UrllibHttpClient` acquire succeeds (title + body + provenance) |
| SSL | **Resolved in code** — `truststore.SSLContext` (OS trust store); root cause was conda/`SSL_CERT_FILE` CA path vs OpenSSL 3 |
| LinkedIn | **Evidence-based unsupported for reliable URL acquire** — classify OK; live redirects to listings; fail closed |
| Indeed | **Evidence-based unsupported for reliable URL acquire** — Cloudflare `HTTP 403`; no bypass |
| New sources | None added (no clean lawful HTTP board beyond SEEK) |
| Ingress | Remains thin (ADR-010 unchanged) |
| Horizon 1A | Unchanged |

**Verdict:** **GO WITH REVISED SCOPE** — ship SEEK as the production URL source; keep LinkedIn/Indeed as attempt/fail-closed; next volume path is email-alert acquisition (M4+), not Playwright.

---

## 2. SEEK production readiness

| Concern | Change / evidence |
|---------|-------------------|
| Canonical URL | Host variants (`www.seek.com.au`, `au.seek.com`) → stable `https://www.seek.com.au/job/<id>` |
| Identity | `platform_job_id` + canonical share across hosts; definite skip still FR-009 reuse |
| Provenance | `source_kind=url`, canonical `source_url` / `source_identifier`, `acquired_at` |
| Extract | Title cleaning (`… Job in … - SEEK` → role title); company left unset when only board brand is available (fail closed vs inventing employer) |
| Redirect | `www` → `au.seek.com` recorded as warning; acquisition still succeeds |
| Errors / UX | Clearer CLI hints on failure; offline fixtures unchanged |
| Live | `UrlAcquisitionAdapter` + `UrllibHttpClient` acquired SEEK job `93312273` (title `AI Engineer`, raw ~1.7k chars) |

Owner experience: `cic opportunity discover <seek-job-url>` is the production paste path once analysis credentials are present (or `--offline-fixtures` for smoke).

---

## 3. SSL investigation

### Root cause (environment, not architecture)

| Fact | Detail |
|------|--------|
| Symptom | `CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked critical` |
| Default verify paths | Conda `Library/ssl/cacert.pem`; `SSL_CERT_FILE` pointed at that bundle |
| `certifi` alone | Still failed (`unable to get local issuer certificate`) |
| `truststore.inject_into_ssl()` | Still failed (global inject does not override broken env CA for all hosts) |
| `truststore.SSLContext(PROTOCOL_TLS_CLIENT)` | **Succeeds** — uses Windows OS certificate store |
| `curl.exe` | Already succeeded (same OS store) |

**Conclusion:** Local Python was verifying against a conda CA bundle that OpenSSL 3 rejects for these hosts. System TLS was fine. This is an **environment/configuration defect**, not a board or adapter design defect.

### Solution

- Production code: `UrllibHttpClient` uses `build_default_ssl_context()` → prefer `truststore.SSLContext`, else stdlib default. Verification remains **on**.
- Dependency: declare `truststore>=0.10.0` in `pyproject.toml` (already present in the owner env; now explicit).
- No certificate pinning, no `CERT_NONE`, no anti-bot bypass.

### Production code changes required?

**Yes, narrowly:** discovery HTTP client must construct an OS-backed SSL context. No Horizon 1A changes. CLI `inject_into_ssl()` for OpenAI remains separate and optional.

---

## 4. LinkedIn investigation

| Approach | Result |
|----------|--------|
| Plain HTTP GET of `/jobs/view/<id>` | Often **200** but final URL `?trk=expired_jd_redirect` → search listing |
| Slug URLs `/jobs/view/…-<id>` | **Normalised** (M3) to numeric canonical — classify works; acquire still fails closed on listing |
| Metadata / public endpoints | No stable undocumented public job JSON used — would be brittle / ToS-risk |
| Login / session | Rejected — out of principles |
| Playwright | Rejected — automation theatre |

**Recommendation:** Keep LinkedIn on the allow-list as an **attempt** path with fail-closed quality gates (`expired_jd_redirect`, listing titles, non-`/jobs/view/` finals). Do **not** claim production LinkedIn URL acquire. Prefer **email-alert / paste** later for LinkedIn volume.

---

## 5. Indeed investigation

| Approach | Result |
|----------|--------|
| Plain HTTP `viewjob?jk=` | **HTTP 403** Cloudflare challenge |
| Alternate headers / UA | Not pursued as bypass theatre |
| Public API | No owner-approved Indeed API integration in scope |
| Playwright / challenge solve | Rejected |

**Recommendation:** Keep Indeed classify + fail-closed on 403/challenge. Document limitation. Email alerts / paste for Indeed volume later. **Do not bypass anti-bot.**

---

## 6. Newly supported sources

**None.** No additional board met “robust, lawful, maintainable plain HTTP” without browser automation. Architecture remains extensible via `SUPPORTED_PLATFORMS` + `derive_source_facets` + extractor regions.

---

## 7. Sources remaining unsupported (URL path)

| Source | Classification | Why |
|--------|----------------|-----|
| LinkedIn (reliable live job body) | Attempt / fail closed | Listing redirects & walls without login/browser |
| Indeed (reliable live job body) | Attempt / fail closed | Cloudflare challenge on plain GET |
| Company careers pages | `unsupported_source` | Not allow-listed; no generic site scraper |

Paste/export (Horizon 1A) remains the universal fallback.

---

## 8. Engineering decisions

| Decision | WHY | Alternative | Rejected because | Principle | Interview takeaway |
|----------|-----|-------------|------------------|-----------|--------------------|
| `truststore.SSLContext` in fetch client | Fix env TLS without disabling verify | Ignore SSL / CERT_NONE | Security theatre & false “board blocked” signal | Fail closed; validate first | Separate env defects from product defects |
| Stable SEEK `www.seek.com.au` canonical | Idempotency across host redirects | Preserve raw netloc | Duplicate false misses across www/au | Explicit provenance | Canonicalise identity, not page chrome |
| LinkedIn listing/redirect gate | Prevent false Opportunities from search HTML | Accept any long HTML | Pollutes SoT | Fail closed | HTTP 200 ≠ usable job ad |
| No Playwright for LinkedIn/Indeed | Lawful maintainability | Browser automation | Scrape theatre; fragile | No automation theatre | Unsupported is a valid engineering answer |
| No new boards | Dual-value / evidence | Add Jora/etc. without live proof | Scope expansion without validation | Validate first | Extensibility ≠ premature allow-list growth |
| Ingress stays thin | ADR-010 | Fat discovery orchestrator | Reopens FR-008 | Thin interfaces; reuse | Coordinator ≠ second OS |

---

## 9. Test results

| Suite | Result |
|-------|--------|
| `tests/unit/discovery/` | **47 passed** |
| `tests/unit/opportunities/test_identity.py` | passed (incl. SEEK canonical + LinkedIn slug) |
| Broader: discovery + identity + duplicates + orchestration models + FR-008 functional | **105 passed** |

New coverage: SSL context construction; SEEK host canonical; LinkedIn slug classify; listing/redirect fail-closed; Indeed 403 mapping; ingress acquire + definite skip; injected SSL context on `urlopen`.

---

## 10. Manual validation (M3 live)

Client: production `UrllibHttpClient` (truststore SSL). No Playwright. No Opportunity persist required for this table (acquire-only).

| Source | Classify | Fetch / extract | Support |
|--------|----------|-----------------|---------|
| SEEK `…/job/93312273` | seek / id / canonical | **OK** — title `AI Engineer`, usable body | **SUPPORTED** |
| LinkedIn `/jobs/view/4429615445` | linkedin | `blocked_response` (expired redirect listing) | **UNSUPPORTED (reliable)** |
| LinkedIn slug URL | linkedin (slug→id) | `blocked_response` | **UNSUPPORTED (reliable)** |
| Indeed `jk=6449f2b22e094d45` | indeed | `http_error` HTTP 403 | **UNSUPPORTED (reliable)** |
| Thoughtworks careers | unsupported_source | n/a | **UNSUPPORTED** |

Owner UX: failure messages include paste/export hint; unsupported hosts explain allow-list.

---

## 11. Documentation updated

- This report; changelog § 1.120
- ADR-010 M3 note; testing strategy; implementation notes
- Functional specification (FR-018 status); roadmap; phase history
- README / AGENTS / repository guide (status only)

---

## 12. Learning outcomes

1. **Environment vs platform:** Conda CA + OpenSSL 3 looked like “boards block Python”; OS trust store proved otherwise for SEEK.
2. **200 is not success:** LinkedIn listing redirects are the classic false-positive acquisition hazard.
3. **Unsupported is deliverable:** Documented LinkedIn/Indeed limits beat brittle bypasses.
4. **Thin ingress held:** Hardening stayed in HTTP/classify/extract — not a second orchestrator.

---

## 13. Recommendation

**M3 COMPLETE — GO WITH REVISED SCOPE**

- Treat **SEEK URL discover** as production-ready.
- Leave LinkedIn/Indeed as classify-and-fail-closed attempts.
- **M4 direction:** email-alert (or export) acquisition for volume — not Playwright, not LinkedIn/Indeed scrape escalation.
- Stop before M4.

---

## 14. Final repository status

| Item | Status |
|------|--------|
| Horizon 1A | Frozen / unchanged |
| FR-018 M0–M2 | Accepted |
| FR-018 M3 | **Complete — GO WITH REVISED SCOPE** |
| M4 | Not started |

**M3 COMPLETE — GO WITH REVISED SCOPE**
