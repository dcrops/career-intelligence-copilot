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
- May activate navigation/entry controls (`Apply` / `Quick apply` on job detail, `Continue`, `Next`).
- Cover-letter method radio must be **checked and verified** before upload/Continue.
- Continue only counts as progress when application **state changes** (step/URL/marker); validation banners mean failure.
- Same application state: max **2** failed advances, then OWNER PAUSE (no click loop).
- At **Review and submit**: automation stops, **browser stays open**, owner submits manually; spike closes only after `OWNER_END_SESSION`.
- If classification is ambiguous → pause and ask the owner.
- No SEEK passwords stored. Dedicated Playwright Chromium profile only.
- Does not regenerate CV/cover-letter artefacts.

## Preserved runs

- `spikes/aas0/runs/20260812T042513Z` — PARTIAL (cover-letter loop)
- `spikes/aas0/runs/20260812T065805Z` — assistance PASS; submission NOT COMPLETED (browser closed before owner Submit)

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
python -m pytest tests/spikes/test_aas0_*.py -q
```

## Report

After the live run, fill `docs/spikes/application_assistance_aas0.md`.
