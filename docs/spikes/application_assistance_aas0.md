# AAS-0 Application Assistance Spike Report

## Accurate application state (mandatory)

| Result | Value |
|--------|--------|
| Browser-assistance result | **PASS** |
| Application submission | **NOT COMPLETED** |
| Reason | Spike lifecycle closed the Playwright browser after reaching Review and submit, before the owner could manually click Submit application |
| Pipeline / opportunity | **Do not** record Repurpose It as applied/submitted |

Preserved runs:

- Failure (cover-letter loop): `spikes/aas0/runs/20260812T042513Z`
- Assistance PASS / submit incomplete: `spikes/aas0/runs/20260812T065805Z`

---

## 1. Objective

Test whether Playwright-assisted application can materially reduce owner attention for one real SEEK-native job application, stopping before final Submit.

## 2. Target application

- Company: REPURPOSE IT P/L · AI Engineer · `opp_01KZQJY6AX3EGX7TGYTHR3ABG1`
- **Limitation:** SEEK-native experiment (not general ATS)

## 3–4. Architecture / browser

Disposable `spikes/aas0/` + dedicated Playwright profile. No production CIC integration.

## Post-run dogfood fixes (spike-only; not live-retested yet)

1. **Browser remains open at final review** — automation stops, verifies Submit control exists, waits for `OWNER_END_SESSION`, optionally observes post-submit page text, then closes. Never clicks Submit.
2. **SEEK CV rotation** — classification helper + notes; no destructive delete automation until external filenames make replaceable docs reliable. See `NOTES_SEEK_CV_ROTATION.md`.
3. **External filenames** — proposed packaging/export ownership + helper. See `NOTES_EXTERNAL_FILENAMES.md`.

## 15. Product verdict

**PASS** (browser assistance) · **NOT COMPLETED** (application submission)

## 16. Recommendation

**Move to AAS-1 prep** (external filenames + CV rotation + keep-alive handoff already spiked) rather than immediately retesting Repurpose It, unless the owner wants to actually submit this application with the new keep-alive behaviour (**RETEST Repurpose It** for submit handoff only).
