# AAS-0 Application Assistance Spike Report

Document quality remediation is **complete**
([eval/document_quality_remediation.md](../eval/document_quality_remediation.md)).
AAS-0.1 is **paused, not complete** (20 Aug 2026 close-out). Resume from this
spike rather than restarting Playwright from scratch. Do not prioritise Indeed
ingestion ahead of AAS continuation.

## Accurate application state (mandatory)

| Result | Value |
|--------|--------|
| Browser-assistance result | **PASS with residual defect** (12 Aug 2026; 19 Aug Repurpose owner-submitted; 20 Aug CSK owner-submitted). Employer-question owner-resume remains **open**. |
| Application submission (AAS) | **Never clicked Submit** |
| Novigi 19 Aug 2026 (`20260819T064132Z`) | Reached Review with **wrong CV** (Repurpose); cover letter correct; **not submitted** |
| Global 360 19 Aug 2026 (`20260819T073606Z`) | Corrected AAS **stopped** (`expected_cv_not_present`); Novigi CV stayed selected; Upload spinner active; **not submitted** |
| Global 360 19 Aug 2026 (`20260819T082816Z`) | Stopped `oldest_age_order_ambiguous` (mixed age metadata); Default unchanged; Novigi CV still selected; **not submitted** |
| Global 360 19 Aug 2026 (`20260819T083640Z`) | Stopped `overflow_not_found_on_row`; candidate was the Global 360 **cover letter** PDF, not a saved résumé; **not submitted** |
| Global 360 19 Aug 2026 (`20260819T091149Z`) | Stopped `resume_delete_confirmation_unobserved`; confirmation dialog now observed (Delete/Cancel); **not submitted** |
| Global 360 19 Aug 2026 (`20260819T100739Z`) | Confirmation Delete succeeded; SEEK removed the row; AAS stopped `deleted_filename_count_unexpected` before list refresh; **not submitted** |
| Global 360 19 Aug 2026 (`20260819T102039Z`) | Expected Global 360 CV selected; structural Default badge moved onto that CV; AAS stopped `default_checkbox_remained_checked` while the checkbox looked unchecked; **not submitted** |
| Hatch 19 Aug 2026 (`20260819T110646Z`) | Rotation deleted Intelligen CV; Default unchanged; Hatch cover letter uploaded; Hatch CV never appeared (`retry_outcome=expected_cv_not_present`); **not submitted** |
| Hatch 19 Aug 2026 (`20260819T112309Z`) | Hatch CV appeared and was selected; `uncheck()` threw `Clicking the checkbox did not change its state`; checkbox then settled unchecked and Default restored to the AI Engineer CV; AAS had treated the exception as terminal; **not submitted** |
| Hatch 19 Aug 2026 (`20260819T114421Z`) | Hatch CV + CL attached and selected; Default unchanged; Continue advanced; AAS falsely STOPped `expected_cv_not_present` / `no_non_default_resume` on employer questions (completed stepper text); owner completed Review and submitted; SEEK showed application sent; **AAS did not click Submit** |
| CSK 20 Aug 2026 (`20260820T002128Z`) | Hidden-input résumé path; rotation deleted Attribute Group CV; expected CSK CV never selected (`expected_cv_not_present`); **not submitted** |
| CSK 20 Aug 2026 (`20260820T004048Z`) | Controlled experiment: visible résumé Upload + filechooser delivered the expected filename; SEEK saved count 9→10; CSK CV became structural Default; **not submitted** |
| CSK 20 Aug 2026 (`20260820T012418Z`) | Production Upload against a full library; expected CV already saved; SEEK **Résumé limit reached**; AAS misclassified `no_filechooser_event`; **not submitted** |
| CSK 20 Aug 2026 (`20260820T021350Z`) | Reused already-saved CSK CV; CSK was committed Default; checkbox checked **and disabled**; `uncheck()` timed out `element is not enabled`; **not submitted** |
| CSK 20 Aug 2026 (`20260820T030436Z`) | Reused already-saved CSK CV; generic Default unchanged; exact CSK CV + cover letter on Review; owner answered employer questions in the browser; AAS then blocked on UNKNOWN / AMBIGUOUS APPLICATION QUESTION (`OWNER_ANSWER` only); SKIP used three times; Review handoff; owner submitted (`likely_submitted` / `apply_success_url`); **AAS did not click Submit** |
| Pipeline / opportunity | CSK `opp_01M0E6GQ9XQH9DK9N5T0MS67N0` owner-submitted 20 Aug 2026; Global 360 `opp_01KZQK08P757DCAE1RM5GPPKC6` paused; Novigi `opp_01M0CBFRA0SQR1769T6KTKJ6RK` previously paused at Review |

Preserved runs:

- Failure (cover-letter loop): `spikes/aas0/runs/20260812T042513Z`
- Assistance PASS / submit incomplete: `spikes/aas0/runs/20260812T065805Z`
- AAS-0.1 live (owner Submit success; Default + observation defects): `spikes/aas0/runs/20260819T042502Z`
- AAS-0.1 Novigi wrong-CV at Review: `spikes/aas0/runs/20260819T064132Z`
- AAS-0.1 Global 360 expected-CV missing: `spikes/aas0/runs/20260819T073606Z`
- AAS-0.1 Global 360 mixed-age STOP: `spikes/aas0/runs/20260819T082816Z`
- AAS-0.1 Global 360 cover-letter inventory STOP: `spikes/aas0/runs/20260819T083640Z`
- AAS-0.1 Global 360 delete-confirmation STOP: `spikes/aas0/runs/20260819T091149Z`
- AAS-0.1 Global 360 Close/X confirmation STOP: `spikes/aas0/runs/20260819T092325Z`
- AAS-0.1 Global 360 confirmation observation missing: `spikes/aas0/runs/20260819T094223Z`
- AAS-0.1 Global 360 WORD JOINER / Dismiss dump: `spikes/aas0/runs/20260819T095559Z`
- AAS-0.1 Global 360 post-delete list lag: `spikes/aas0/runs/20260819T100739Z`
- AAS-0.1 Global 360 Default-checkbox STOP: `spikes/aas0/runs/20260819T102039Z`
- AAS-0.1 Hatch rotation + missing CV retry: `spikes/aas0/runs/20260819T110646Z`
- AAS-0.1 Hatch Default-checkbox timing: `spikes/aas0/runs/20260819T112309Z`
- AAS-0.1 Hatch false STOP after successful documents / owner submit: `spikes/aas0/runs/20260819T114421Z`
- AAS-0.1 CSK hidden-input dump / rotation: `spikes/aas0/runs/20260820T002128Z`
- AAS-0.1 CSK controlled filechooser experiment: `spikes/aas0/runs/20260820T004048Z`
- AAS-0.1 CSK capacity misclassified as no filechooser: `spikes/aas0/runs/20260820T012418Z`
- AAS-0.1 CSK committed-Default checkbox STOP: `spikes/aas0/runs/20260820T021350Z`
- AAS-0.1 CSK Review + owner Submit; question-gate SKIP workaround: `spikes/aas0/runs/20260820T030436Z`

---

## 1. Objective

Test whether Playwright-assisted application can materially reduce owner attention for one real SEEK-native job application, stopping before final Submit.

## 2. Target application

- Company: Global 360 · AI Engineer · `opp_01KZQK08P757DCAE1RM5GPPKC6` (paused live AAS)
- Prior live: Novigi Pty Ltd · Senior AI Engineer · `opp_01M0CBFRA0SQR1769T6KTKJ6RK`
- Prior: REPURPOSE IT P/L · AI Engineer · `opp_01KZQJY6AX3EGX7TGYTHR3ABG1`
- **Limitation:** SEEK-native experiment (not general ATS)

## 3–4. Architecture / browser

Disposable `spikes/aas0/` + dedicated Playwright profile. No production CIC integration.

## AAS-0.1 corrections (after live run 20260819T042502Z)

Not a new FR. Application Assistance is **not** complete.

### Default résumé observation

Parser uses the résumé **row container** (outermost ancestor that still contains
exactly one `.pdf`), so the visible **Default** badge is included. Selection and
Default remain distinct. Filenames are not special-cased.

### Default checkbox

AAS may still attempt to uncheck **Make this my default résumé** when SEEK
auto-checked it after a **new** upload and the control is still **enabled**.
After `uncheck()` returns or throws, the guard polls the checkbox and the
structural Default until they settle or the bounded wait times out
(~400ms / ~15s). Hatch live run `20260819T112309Z` proved
`Clicking the checkbox did not change its state` can precede a successful
asynchronous restore of the pre-upload Default; that exception is
diagnostic evidence only. Temporary disabled **after** an enabled uncheck
click is SEEK processing, not immediate failure.

CSK live run `20260820T021350Z` proved a different state: selecting an
already-saved résumé that is already structural Default shows the checkbox
checked **and disabled**. That is a committed Default. AAS must not call
`uncheck()`, must not settle-wait, and must not transfer Default onto
another résumé. Discriminator: disabled + checked + selected filename equals
Default → `structural_default_checkbox_locked` STOP. Enabled + checked
remains the Hatch uncheck path.

Success requires the checkbox unchecked **and** the original structural
Default restored. Selected application résumé may remain the uploaded CV.
No automatic restore. Missing pre-upload Default stays fail-closed
(checkbox-only). Timeout / unexpected third Default / unobservable Default →
**STOP**. `default_checkbox_observation.json` still records the transition.
Selectors and `.first` are unchanged. The lock STOP is implemented and
offline-tested; it was **not** live-retested after `20260820T021350Z`
(`20260820T030436Z` had Default already restored, so the checkbox was
unchecked).

### Documents stage vs later pages

Hatch live run `20260819T114421Z` proved the Hatch CV and cover letter were
attached and selected, Default stayed on the AI Engineer CV, and Continue
advanced to Answer employer questions. AAS then treated leftover stepper text
`Choose documents` as the documents page, saw no résumé radios, and STOPped
`expected_cv_not_present` / `no_non_default_resume`. The owner completed
Review (exact Hatch filenames) and submitted; SEEK showed the application
had been sent.

Choose Documents is active only when real documents controls exist (résumé
file input, cover-letter input/radio, or Default checkbox) — not stepper
text. After verified CV + documents gate + Continue `advanced`, the run
latches documents-complete and does not re-enter upload/confirm/rotation.
Empty résumé snapshots on later pages are not upload failure. Final Review
exact-filename gate remains the last-line check. Owner-session teardown
(including STOP/inspection) observes submission success if the page shows it.
CSK `20260820T030436Z` live-proved the documents-complete latch, Review
exact-filename match, and owner-Submit observation. It did **not** prove a
clean employer-question protocol.

### Résumé upload dump

Hatch live run `20260819T110646Z` proved one-delete rotation and Default
protection; the expected Hatch CV never appeared on first upload or retry.
CSK controlled experiment `20260820T004048Z` proved visible résumé Upload +
Playwright filechooser delivers the expected filename; hidden-input
`set_input_files` on `#resume-fileFile` does not. That experiment **changed
SEEK account state** (saved count 9 → 10; expected CSK CV present and became
structural Default). Production `20260820T012418Z` therefore did not start
from the same precondition and did **not** disprove filechooser: Upload hit
**Résumé limit reached** with the expected CV already saved, and AAS
misclassified the missing chooser as `no_filechooser_event`.

Production now reuses an exact already-saved expected CV (no Upload /
filechooser / rotation), classifies the capacity modal as
`resume_capacity_blocked`, and rotates only when that expected CV is absent.
Continue refuses when the expected application CV is also structural Default;
automation does not restore Default by selecting another résumé. Cover-letter
upload is unchanged. Selectors for cover letter, retry count, and Default
policy are unchanged. AAS is **not** complete: employer-question
owner-resume remains open. CSK `20260820T030436Z` live-proved expected-CV
reuse, documents-complete latch, Review exact-filename match, and
no-Submit handoff; it did not re-prove production filechooser upload.

**Temporary owner duty:** after Submit, restore
`David Cropper - AI Engineer CV.pdf` as the SEEK Default if a tailored CV
became Default. Automatic restore is not implemented. CSK
`20260820T030436Z` already had that generic Default restored and left it
unchanged.

### Submission observation

Success if URL contains `/apply/success` **or** visible text contains
`application has been sent` (plus prior phrases). Owner-session teardown
after STOP or Review handoff records that observation. Ending the owner
session alone is not treated as submitted. Automation never clicks Submit.

### Employer-question owner-resume protocol (OPEN)

CSK live run `20260820T030436Z` reached Answer employer questions after
documents Continue. The owner answered the three SEEK questions in the
Playwright window (daily rate, CBD office, years as an AI Engineer) and
moved ahead. AAS then collected those labels as unanswered and blocked on
UNKNOWN / AMBIGUOUS APPLICATION QUESTION.

`ask_question()` waits only for `OWNER_ANSWER.json` or `OWNER_ANSWER.txt`.
`OWNER_CONTINUE` and `OWNER_END_SESSION` do not resume that wait. SKIP was
the safest existing workaround: it skipped filling those fields (the owner
had already filled them) and AAS then reached Review. There is **no**
explicit “owner already handled this question; resume from current page”
capability. This remains an **open issue**. Do not treat AAS-0.1 as complete
while it is unresolved.

### Final-review stage

Stepper text `Review and submit` is **not** sufficient. Handoff requires
positive Review-stage evidence (`Submit application` / `send application`).
Automation still never clicks Submit.

## AAS-0.1 wrong-CV gates (after Novigi run 20260819T064132Z)

Live defect: expected Novigi export CV was not confirmed selected. SEEK kept
`David Cropper - REPURPOSE IT PL - AI Engineer - CV.pdf`. Cover letter was the
correct Novigi export. Upload was asynchronous (Upload spinner still active on
Choose documents). AAS declared APPLICATION READY because Review was reached.

Corrections (not live-retested):

- After résumé Upload filechooser `set_files`, wait until the **exact** expected export filename
  is a résumé row **and** selected. If it appears unchecked, select that radio
  and verify. Missing row, remaining spinner, or another CV still selected →
  **STOP**, browser open, no Continue.
- Choose-documents Continue requires that CV selection **and** cover-letter
  readiness. Correct Default does **not** compensate for a wrong selected CV.
- Before APPLICATION READY, Review must show **both** expected export
  filenames. Mismatch / missing / unobservable → **STOP**, not ready.

Résumé capacity / retained-library lifecycle is treated as operationally
proven enough to justify **bounded** rotation (Novigi owner had to delete a
saved résumé before a manual upload succeeded; Global 360 repeated the same
blocked-upload pattern). Owner policy:

- structural **Default** is protected
- every other saved SEEK résumé is disposable
- delete the oldest non-Default row only after upload failure
- one delete, one upload retry, then fail closed
- no bulk cleanup, no automatic Default restore
- filenames/provenance do not decide deletability

Overflow kebab exposes **Download** and **Delete**. AAS deletes the **oldest
non-Default** row. Age text is used only when every eligible row has it;
mixed/missing age falls back to newest-first list order (last eligible
non-Default). Live `20260819T082816Z` stopped on mixed-age; that stop is
removed. Live `20260819T083640Z` selected the Global 360 cover letter PDF as
the rotation candidate (`overflow_not_found_on_row`). Inventory is now
**saved résumé rows only** — cover-letter files/radios, “Don't include a
résumé”, and upload controls are excluded. Live `20260819T091149Z` showed the
Delete confirmation dialog (prompt + candidate filename, Delete/Cancel/Dismiss).
Live `20260819T095559Z` proved Delete is prefixed with U+2060 WORD JOINER and
the X control is named `Dismiss`. Action names are normalised before
comparison; Cancel, Dismiss, and Close are allowed and never clicked.
Application Assistance is **not** complete until a controlled live retest.

Next: owner should **end** the `20260819T100739Z` Playwright session
(`OWNER_END_SESSION`) if still open, then run one controlled live retest.
Post-delete verification now polls the résumé list boundedly. Do not launch
SEEK from this documentation.

## AAS-0.1 bounded résumé rotation (after Global 360 `20260819T073606Z`)

Trigger (not on every apply): expected CV missing / spinner timeout / still
processing / observable capacity message.

Then: inventory **saved résumé rows only** → skip structural Default → one
oldest non-Default row →
open **that** row's three-dot menu → click exact `Delete` → on the observed
confirmation (“Are you sure you want to delete this document?” + candidate
filename) click the single normalised dialog `Delete` (never Cancel, Dismiss,
or Close) → if the dialog does not match, STOP → else **poll** until one row
is gone, Default unchanged (or STOP on timeout / Default change / wrong row)
→ retry expected CV upload **once** → continue only if that exact filename is
present, not busy, and selected.

## Offline whole-flow integration

`tests/spikes/test_aas0_offline_flow_integration.py` exercises the **current**
AAS helpers together without contacting SEEK or launching Playwright.

It covers one Global 360-shaped happy path: export preflight → blocked first
CV upload → saved-résumé inventory (cover letter excluded) → one oldest
non-Default Delete → Default unchanged → one retry with expected CV selected
→ documents Continue → employer-questions / Update SEEK Profile stepper
text is not final Review → Review both export filenames → APPLICATION READY
FOR OWNER with Submit unclicked → owner `/apply/success` observation →
metrics JSON including `review_document_reason`.

Failure checks: wrong CV after retry; Default change during rotation;
Review Novigi CV + Global 360 cover letter; unknown delete confirmation;
metrics serialisation on early STOP.

It does **not** prove live SEEK DOM, real overflow/Delete, login, network,
or confirmation-dialog copy. Application Assistance is **not** complete.
The CSK production path `20260820T030436Z` reused an already-saved CV, so it
did **not** re-prove visible Upload + filechooser. The remaining live gap is
the employer-question owner-resume protocol. Do not launch SEEK from this
documentation.

## Learning item (recorded at 20 Aug 2026 close-out; AAS-0.1 is not complete)

**Browser automation must reproduce the application's semantic interaction
sequence, not merely manipulate equivalent-looking DOM state.** External
account state is part of the experiment precondition: a successful controlled
run that uploads a CV changes SEEK's saved-résumé library, so a later
"clean" production validation is not the same starting state.

Hidden `input#resume-fileFile.set_input_files` looked correct: the input
exists, is enabled, Playwright returns successfully, and cover-letter
upload uses a similar hidden input after the "Upload a cover letter" radio
initialises that widget. Playwright success was insufficient evidence
because SEEK's visible résumé Upload never received the user-gesture
filechooser sequence, so the control stayed disabled/spinning and the
expected filename never appeared. The controlled CSK experiment
(`20260820T004048Z`) isolated the interaction difference by clicking only
the résumé Upload associated with `#resume-fileFile` and using
`page.expect_file_chooser()` / `chooser.set_files`, without cover letter,
rotation, Continue, or Submit. That path remains proven. Production
`20260820T012418Z` failed because the library was already full and the
expected CV already existed; SEEK answered Upload with **Résumé limit
reached** instead of a filechooser. Cover letter remains a useful comparison:
that widget is initialised by selecting the upload-method radio before
hidden-input `set_input_files`, which is why CL succeeded while résumé
hidden injection failed.

## 15. Product verdict

**AAS-0.1 is paused, not complete.** Documents/Review/no-Submit on CSK
`20260820T030436Z` succeeded (exact export filenames; generic Default
unchanged; owner submitted; AAS never clicked Submit). Employer-question
owner-resume remains **unresolved**. Filechooser production upload was
live-proven only in the controlled experiment `20260820T004048Z`, not in
that CSK production run. `structural_default_checkbox_locked` is implemented
and offline-tested; it was **not** live-retested as a STOP after
`20260820T021350Z` (the later run had Default already restored).

## 16. Recommendation

Pause AAS-0.1 here. Resume later at the employer-question owner-resume
protocol (owner already answered in the browser; `OWNER_CONTINUE` /
`OWNER_END_SESSION` must not be the only way out of `OWNER_ANSWER` wait).
Do not treat Application Assistance as complete. Do not launch SEEK from
this documentation.
