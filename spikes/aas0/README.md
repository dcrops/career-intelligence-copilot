# AAS-0 — Application Assistance Spike (disposable)

Engineering spike only. Not a production FR. Not wired into `cic`.

## Limitation

This experiment is **SEEK-native** application assistance for:

- Repurpose It — AI Engineer
- `opp_01KZQJY6AX3EGX7TGYTHR3ABG1`
- https://www.seek.com.au/job/93837541

It is **not** a general Greenhouse/Lever/employer-ATS experiment.

If SEEK shows CAPTCHA, anti-bot behaviour, or an unexpectedly hostile flow:
**STOP and report**. Do not switch targets automatically.

## Safety

- Never activates irreversible final-submission controls.
- Uploads only package `export/` PDFs (`… - CV.pdf` / `… - Cover Letter.pdf`);
  refuses internal `opp_<ULID>.pdf`.
- Observes SEEK **Default** badge on the résumé row; never ticks **Make this my default résumé**;
  stops if the checkbox stays checked after uncheck, or if Default changes (does not auto-restore).
- After the expected CV is present and selected, uncheck **Make this my default résumé**
  if SEEK auto-checked it **and the checkbox is still enabled**, then wait until the
  pre-upload structural Default is restored.
- If that checkbox is checked **and disabled** on the already-Default selected
  résumé: STOP `structural_default_checkbox_locked`. Do not uncheck. Do not
  transfer Default onto another résumé.
- If the exact expected CV is already saved, select it; do not Upload, wait for
  filechooser, or rotate. Record `existing_expected_cv_reused`.
- Résumé upload uses the visible Upload control associated with `#resume-fileFile`
  plus Playwright filechooser. It does not inject files into the hidden input.
  Upload click may produce a filechooser **or** SEEK **Résumé limit reached**;
  the latter is `resume_capacity_blocked`, not `no_filechooser_event`.
- On proven capacity/upload failure **and** expected CV absent: deletes **one** oldest
  non-Default saved résumé
  (Default badge protected; all other SEEK résumés are disposable). Row-scoped
  overflow **Delete**. Confirmation dialog → stop. Then one expected-CV retry.
- If the expected application CV is also structural Default, STOP for owner
  correction. Do not restore Default by selecting another résumé.
- Handoff only on positive Review evidence (`Submit application`) **and** both expected
  CV and cover-letter filenames visible on Review. Stepper text `Review and submit` is not enough.
- Observes owner Submit via `/apply/success` or `application has been sent` (plus prior phrases).
- May activate navigation/entry controls (`Apply` / `Quick apply` on job detail, `Continue`, `Next`).
- Cover-letter method radio must be **checked and verified** before upload/Continue.
- Continue only counts as progress when application **state changes** (step/URL/marker); validation banners mean failure.
- Same application state: max **2** failed advances, then OWNER PAUSE (no click loop).
- At **Review and submit**: automation stops, **browser stays open**, owner submits manually; spike closes only after `OWNER_END_SESSION`.
- If classification is ambiguous → pause and ask the owner.
  Question wait accepts only `OWNER_ANSWER.json` / `OWNER_ANSWER.txt`
  (`SKIP` skips the field). `OWNER_CONTINUE` / `OWNER_END_SESSION` do not
  resume that wait. There is no “owner already handled this; resume from
  the current page” path (CSK `20260820T030436Z`; **open**).
- No SEEK passwords stored. Dedicated Playwright Chromium profile only.
- Does not regenerate CV/cover-letter artefacts.

## Preserved runs

- `spikes/aas0/runs/20260812T042513Z` — PARTIAL (cover-letter loop)
- `spikes/aas0/runs/20260819T042502Z` — AAS-0.1 live; owner Submit succeeded; Default/observation/handoff defects diagnosed
- `spikes/aas0/runs/20260819T064132Z` — Novigi; wrong previous-opportunity CV at Review; not submitted
- `spikes/aas0/runs/20260819T073606Z` — Global 360; expected CV missing; corrected AAS stopped; not submitted
- `spikes/aas0/runs/20260819T082816Z` — Global 360; mixed-age STOP (`oldest_age_order_ambiguous`); not submitted
- `spikes/aas0/runs/20260820T004048Z` — CSK controlled filechooser experiment; account state changed; not submitted
- `spikes/aas0/runs/20260820T021350Z` — CSK committed-Default checkbox STOP; not submitted
- `spikes/aas0/runs/20260820T030436Z` — CSK Review exact filenames; owner submitted; question-gate SKIP workaround; AAS did not click Submit

## Setup (once)

From repo root, in the project venv:

```powershell
pip install -r spikes/aas0/requirements-spike.txt
playwright install chromium
```

Do **not** add Playwright to production `pyproject.toml` for this spike.

## Commands

### Offline preflight (safe; no browser)

```powershell
$env:PYTHONPATH = "src;spikes"
python spikes/aas0/run_assist.py --preflight-only
```

### Live run (requires explicit owner authorization)

```powershell
$env:PYTHONPATH = "src;spikes"
python spikes/aas0/run_assist.py --authorize-live
```

Dedicated profile directory: `spikes/aas0/.browser-profile/`  
Metrics/screenshots: `spikes/aas0/runs/<timestamp>/`

## Primary metric

**Owner active-attention time** (not wall-clock browser time).

Also recorded: total elapsed, automation runtime, waiting time.

## Tests

```powershell
$env:PYTHONPATH = "src;spikes"
python -m pytest tests/spikes/test_aas0_*.py tests/unit/application_package/test_external_upload.py -q
```

## Report

After the live run, fill `docs/spikes/application_assistance_aas0.md`.
