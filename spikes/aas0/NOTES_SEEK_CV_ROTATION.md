# AAS spike notes — SEEK CV storage / rotation (AAS-0.1)

Access basis: AAS-0 live Choose Documents screenshots
(`spikes/aas0/runs/20260812T042513Z`, `20260812T065805Z`,
`20260819T042502Z`, `20260819T064132Z`, `20260819T073606Z`) + owner
policy (19 Aug 2026). No Playwright/SEEK launch in this documentation slice.

## Lifecycle (authoritative)

| Class | Rule | Auto-delete? |
|-------|------|----------------|
| **Protected** | SEEK structurally marks the row **Default** | Never |
| **Disposable** | Every other saved résumé | Yes — **one** oldest non-Default row after upload failure |

Filename, company, role, `opp_<ULID>.pdf` provenance, and human-readable vs
underscore names do **not** decide deletability. The Default badge is the
protect rule. Example Default filename (`David Cropper - AI Engineer CV.pdf`)
is evidence only.

## Inventory (saved résumé rows only)

Rotation inventory is the SEEK **Résumé** saved-row list. Exclude:

- cover-letter filenames (`… Cover Letter.pdf`) and cover-letter method radios
- upload controls
- **Don't include a résumé**
- any PDF outside the saved résumé list / without saved-row structure

Live `20260819T083640Z` selected the Global 360 cover letter PDF as the
oldest candidate (`overflow_not_found_on_row`). That file is not a résumé.

## Overflow menu (owner observation, 19 Aug 2026)

- Download
- **Delete** (exact destructive label)

## Confirmation (live `20260819T091149Z`)

Dialog: **Are you sure you want to delete this document?** plus the exact
candidate filename (example: `David Cropper Forward Deployed AI Engineer CV.pdf`).
Actions: **Delete** and **Cancel**.

AAS requires one visible `dialog`/`alertdialog`, that prompt, the chosen
filename, and exactly one dialog **Delete**. It clicks only that Delete.
Never Cancel. Never a page-level Delete. Filename mismatch, missing
filename, multiple dialogs, or multiple Delete actions → STOP.

## Definition of oldest

Prefer parsed per-row `Added … ago` when **every** eligible (non-Default) row
has it. Oldest = largest duration.

Otherwise (no age, or mixed age/no-age): use observed newest-first list order
from live Choose Documents evidence, including `20260819T082816Z`. Oldest =
**last eligible non-Default row**. Incomplete age metadata does not stop
rotation.

Default is never eligible, even if it is last in the list.

## Duplicate filenames

Rows are distinct UI entities. Duplicate names are allowed. Candidate identity
is the row index. Open that row's overflow only.

## Rotation policy

Trigger only on concrete upload failure (not every apply), and **only when
the exact expected CV is not already saved**:

- `expected_cv_not_present`
- `resume_upload_spinner_timeout` / `resume_upload_still_processing`
- `resume_capacity_blocked` (including SEEK **Résumé limit reached**)

If the exact expected filename is already in the saved library: reuse it.
Do not Upload. Do not rotate merely because the library is full.

Then (expected CV absent + proven trigger): inventory **saved résumé rows only**
(exclude cover-letter files/radios,
upload controls, “Don't include a résumé”) → skip Default → delete **one**
oldest non-Default (menu Delete, then observed confirmation Delete; Cancel,
Dismiss, and Close are never clicked; action names are normalised) → poll
until the inventory shows count −1 / chosen row gone / Default unchanged →
verify
(count −1, intended row gone, Default observable and unchanged) → retry
expected CV upload **once** via the same visible Upload + filechooser path →
continue only if that exact filename is present,
not busy, and selected.

No bulk cleanup. No second deletion. No automatic Default restore.
If expected CV is already selected: do not rotate.
If expected CV is also the structural Default: STOP for owner correction;
do not restore Default by selecting another résumé. If **Make this my default
résumé** is checked **and disabled** on that selected Default row, classify
`structural_default_checkbox_locked` and do not call `uncheck()` (CSK
`20260820T021350Z`). Checked **and enabled** after a new upload remains the
Hatch uncheck + settle path (`20260819T112309Z`).

Rotation and CV confirm run only while Choose Documents **controls** are
present and the documents stage is not yet complete. Completed stepper text
`Choose documents` on employer questions is not a documents page (Hatch
`20260819T114421Z`). After verified Continue-advanced, do not re-enter
upload/confirm/rotation. Empty later-page résumé snapshots are not
`expected_cv_not_present`.

Offline whole-flow composition is covered by
`tests/spikes/test_aas0_offline_flow_integration.py` (no SEEK / no Playwright).
CSK `20260820T030436Z` live-proved expected-CV reuse, documents-complete
latch, Review exact-filename match, and no-Submit handoff. Employer-question
owner-resume remains **open**. Do not launch SEEK from this documentation.
