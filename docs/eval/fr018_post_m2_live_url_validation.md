# FR-018 Post-M2 — Live URL Validation

**Status:** Complete (validation only — **M3 not started**)  
**Date:** 2026-08-07  
**Phase:** Horizon 1B (FR-018)  
**Preceding:** [M2](fr018_m2_url_discovery_ingress.md) (**GO WITH REVISED SCOPE**)  
**Evidence JSON:** [fr018_post_m2_live_url_validation_20260807T062952Z.json](fr018_post_m2_live_url_validation_20260807T062952Z.json)  
**Runner:** `scripts/run_fr018_post_m2_live_url_validation_curl.py`

---

## 1. Executive summary

Owner-controlled live validation exercised the existing FR-018 M2 URL path against
a small public set (SEEK, LinkedIn ×2, Indeed, optional company careers).

**Findings:**

| Source | Live support |
|--------|----------------|
| SEEK job detail | **SUPPORTED** — usable job HTML via lawful plain HTTP (system TLS) |
| LinkedIn job view | **PARTIALLY_SUPPORTED** — classifies; HTTP 200 often redirects to search/list (`expired_jd_redirect`); not a usable single job ad |
| Indeed `jk=` | **BLOCKED / UNSUPPORTED** — Cloudflare challenge (`HTTP 403`) |
| Company careers | **BLOCKED / UNSUPPORTED** — correctly rejected as `unsupported_source` |

Production `UrllibHttpClient` failed all board fetches on this host with
`network_failure` / `CERTIFICATE_VERIFY_FAILED` (Python SSL trust). Board
accessibility was therefore confirmed with `curl.exe` (Windows cert store) + the
same M2 `classify_supported_job_url` / `extract_job_content_from_html` path. No
Playwright, no anti-bot bypass, no login, no adapter redesign, no Opportunity
persistence, no M3.

**URL-first hypothesis (multi-board):** did **not** survive for LinkedIn/Indeed.  
**URL-first hypothesis (at least one meaningful source):** **survived** — SEEK.

**Recommended M3 direction: A — operationalise URL acquisition** (SEEK-first;
fix Python CA trust for `UrllibHttpClient`; do **not** escalate LinkedIn/Indeed
with browsers). Email-alert acquisition remains the right *later* path for
LinkedIn/Indeed volume — not Playwright.

---

## 2. URLs / sources tested

| Label | URL | Intent |
|-------|-----|--------|
| SEEK | `https://www.seek.com.au/job/93312273` | SEEK job detail |
| LINKEDIN | `https://www.linkedin.com/jobs/view/4429615445` | LinkedIn job view |
| LINKEDIN_ALT | `https://www.linkedin.com/jobs/view/4436067784` | Second LinkedIn job view |
| INDEED | `https://au.indeed.com/viewjob?jk=6449f2b22e094d45` | Indeed with `jk=` |
| CAREERS | `https://www.thoughtworks.com/careers/jobs/7920279` | Optional company careers |

Method per URL:

1. `classify_supported_job_url` (M2)
2. Production `UrllibHttpClient.get` outcome
3. `curl.exe -sL` GET (system TLS) — status, final URL, body
4. `extract_job_content_from_html` (same extractor as `UrlAcquisitionAdapter`)
5. Live quality gate (reject LinkedIn search/list redirects)
6. Provenance / identity facets from canonical URL
7. Opportunity outcome recorded as **would_create_if_persisted** / **failed** (no persist)

---

## 3. Result per source

### SEEK — **SUPPORTED**

| Field | Result |
|-------|--------|
| Classification | allow-listed `seek` / id `93312273` / canonical `https://www.seek.com.au/job/93312273` |
| Production urllib | **failed** `network_failure` (SSL `CERTIFICATE_VERIFY_FAILED`) |
| curl HTTP | **200** → `https://au.seek.com/job/93312273` (~177 KB HTML) |
| Usable job content | **Yes** — title `AI Engineer Job in Cremorne, Melbourne VIC - SEEK` |
| Opportunity | would_create_if_persisted (not written) |
| Failure category | none (curl path); urllib: `network_failure` |

### LinkedIn — **PARTIALLY_SUPPORTED**

| Field | LINKEDIN | LINKEDIN_ALT |
|-------|----------|--------------|
| Classification | `linkedin` / `4429615445` | `linkedin` / `4436067784` |
| Production urllib | SSL `network_failure` | SSL `network_failure` |
| curl HTTP | 200 | 200 |
| Final URL | `.../jobs/digital-project-manager-jobs?trk=expired_jd_redirect` | `.../jobs/belong-jobs?trk=expired_jd_redirect` |
| Extracted title | listing-style (“1,000+ … jobs…”) | listing-style (“72,000+ … jobs…”) |
| Usable single job | **No** | **No** |
| Failure category | `linkedin_expired_or_search_redirect` | same |
| Opportunity | failed | failed |

Note: slug-style AU URLs such as
`/jobs/view/senior-ai-engineer-at-fyndr-group-4429615445` fail classification
today (`platform_job_id` not derived) — expected M2 strictness, not a live HTTP
finding.

### Indeed — **BLOCKED / UNSUPPORTED**

| Field | Result |
|-------|--------|
| Classification | allow-listed `indeed` / `jk=6449f2b22e094d45` |
| Production urllib | SSL `network_failure` |
| curl HTTP | **403** Cloudflare challenge (`captcha` / challenge body ~27 KB) |
| Usable job content | No |
| Failure category | `http_403` / cloudflare challenge |
| Opportunity | failed |

### Company careers — **BLOCKED / UNSUPPORTED**

| Field | Result |
|-------|--------|
| Classification | `unsupported_source` (host not SEEK/LinkedIn/Indeed) |
| curl HTTP | 404 (page also not a supported board) |
| Failure category | `unsupported_source` |
| Opportunity | failed |

---

## 4. Provenance / identity observations

- SEEK: facets stable (`seek`, numeric job id, canonical `/job/<id>`). Redirect
  `www.seek.com.au` → `au.seek.com` does not break identity when canonical is
  derived from the owner URL.
- LinkedIn: numeric `/jobs/view/<id>` classifies and derives facets; live final
  URL after expiry is **not** the job view — provenance would be wrong if we
  blindly trusted extracted listing HTML.
- Indeed: `jk=` classifies and canonicalises to `www.indeed.com/viewjob?jk=…`;
  fetch never reaches extract.
- Careers: correctly fail-closed before fetch for acquisition purposes.
- No Opportunity YAML was created (validation intentionally non-mutating).

---

## 5. Failures and limitations

1. **Python SSL trust on this host** — `UrllibHttpClient` cannot complete TLS to
   SEEK/LinkedIn/Indeed (`CERTIFICATE_VERIFY_FAILED`). Google still verifies;
   certifi alone did not fix board hosts (likely local CA / MITM trust gap).
   Owner must repair Python CA trust before live `cic opportunity discover`
   works even for SEEK.
2. **LinkedIn** — lawful plain HTTP often yields login/search theatre or expired
   redirects, not job ads. Not fixed by scraping harder.
3. **Indeed** — Cloudflare bot challenge on plain GET.
4. **Extractor** — long listing HTML can pass length checks; live validation
   applied an extra quality gate for LinkedIn redirects (report-only; adapter
   not redesigned).
5. **Out of scope (honoured)** — no Playwright, no session theft, no email
   ingestion, no Horizon 1A changes, no M3.

---

## 6. Did the URL-first hypothesis survive?

| Claim | Survived? |
|-------|-----------|
| Owner-pasted URL → usable Opportunity content for **at least one** major board | **Yes — SEEK** |
| SEEK / LinkedIn / Indeed are all reliably usable via lawful plain HTTP | **No** |
| Multi-board URL-first as the sole volume strategy | **No** |

Overall: **partial survival** — enough for option A (one meaningful source), not
enough to claim LinkedIn/Indeed URL operationalisation.

---

## 7. Recommended M3 direction

### **A. M3 = operationalise URL acquisition**

**Chosen.** SEEK is a meaningful real source with usable job content over lawful
plain HTTP (when TLS trust works). Per the post-M2 decision rule, that unlocks A.

**M3 scope (when owner starts M3 — not this task):**

- Fix / document Python CA trust so production `UrllibHttpClient` matches system
  TLS behaviour for SEEK.
- Operational polish for owner URL paste / small batch around the **SEEK** path
  already delivered in M2.
- Keep LinkedIn/Indeed as fail-closed attempt paths; do **not** add Playwright or
  login handling.
- Treat **email-alert acquisition** as the subsequent milestone for LinkedIn /
  Indeed (and SEEK volume), not as a scrape workaround.

**Rejected for M3:** B as the *primary* next milestone only if the owner prefers
volume from LinkedIn/Indeed over polishing the proven SEEK URL path. B remains
valid as M4+ and should not be blocked by A.

---

## 8. Final repository status

| Item | Status |
|------|--------|
| Horizon 1A | Frozen |
| FR-018 M0–M2 | Accepted (M2 = GO WITH REVISED SCOPE) |
| Post-M2 live URL validation | **Complete** (this report) |
| FR-018 M3 | **Not started** |
| Playwright / email ingestion / Horizon 1A changes | Not done (correctly) |

**POST-M2 LIVE VALIDATION COMPLETE — recommend M3 = A (SEEK-first URL ops); do not start M3 in this task.**
