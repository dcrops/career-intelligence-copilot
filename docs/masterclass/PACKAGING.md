# Masterclass packaging — implementation note

**Date:** 2026-08-07 (updated: Interview Brief + Interview Deck layers; FR-018
package; **automatic sibling PDFs** for Lean Masterclass + `sources/` +
`sources/optional/`)  
**Scope:** FR-016, FR-017, and FR-018 packages; pattern for future frozen FRs  
**Related:** [masterclass/README.md](README.md),
[LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md),
[MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md),
[INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md),
[INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md),
[FR016/MANIFEST.md](FR016/MANIFEST.md),
[FR017/MANIFEST.md](FR017/MANIFEST.md),
[FR018/MANIFEST.md](FR018/MANIFEST.md),
`scripts/build_masterclass_package.py`,
`scripts/render_masterclass_pdf.py`

## How authoritative documentation is preserved

Engineering continues to live only under repository SoT paths (`docs/eval/`,
`docs/adr/`, functional specification, domain model, implementation notes, testing
strategy). The Masterclass package never becomes the edit surface.

## How duplication is avoided

`sources/` files are **generated snapshots** (full-file copy or mechanical heading
extract) with an explicit “DO NOT EDIT” banner and a regenerate command. They are
convenience mirrors for single-folder Academy attachment, not parallel documents.
After SoT changes: re-run the builder; do not patch snapshots by hand.

## PDF study editions (automatic)

Every packaged FR **must** have sibling PDFs for:

| Artefact | PDF |
|----------|-----|
| Lean Masterclass `Engineering_Masterclass_*.md` (when present) | same stem `.pdf` |
| Required `sources/*.md` | same stem `.pdf` beside each Markdown |
| Optional `sources/optional/*.md` | same stem `.pdf` beside each Markdown |

**Default:** `python scripts/build_masterclass_package.py FRnnn` regenerates
Markdown snapshots **and** renders those PDFs.

**Standalone:** `python scripts/render_masterclass_pdf.py --package FRnnn`

**Skip PDFs (Markdown only):** `python scripts/build_masterclass_package.py FRnnn --no-pdf`

Do not hand-edit PDFs. They are formatting-only renders of the Markdown.

## How future FRs should adopt the same model

1. Freeze the FR (acceptance + ADR + navigation).
2. Create `docs/masterclass/FRnnn/{README.md,MANIFEST.md}`.
3. Register source mappings in `scripts/build_masterclass_package.py`.
4. Run `python scripts/build_masterclass_package.py FRnnn`
   (snapshots **and** source/optional PDFs; Lean Masterclass PDF if `.md` exists).
5. Commit the package; attach `FRnnn/` for Academy generation.
6. Generate the Lean Engineering Masterclass
   ([MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md) /
   [LEAN_MASTERCLASS_STANDARD.md](LEAN_MASTERCLASS_STANDARD.md)).
7. Re-run the package builder **or**
   `python scripts/render_masterclass_pdf.py --package FRnnn`
   so the Lean Masterclass PDF is included with sources/optional PDFs.
8. Produce the Gamma **Learning** Presentation (~15–20 slides).
9. Produce the **Interview Brief** (~1 page) per
   [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md).
10. Produce the **Interview Deck** (~3–5 slides) per
    [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md).
11. Use Interview Revision / coaching as needed.

FR-018+ inherits this process automatically — do not rediscover Brief/Deck
structure, the deep-learning vs rapid-revision split, or PDF coverage for
Masterclass + sources + optional documents.

Do not populate FR001–FR015 until the owner requests packaging for those FRs.
Do not regenerate FR-016 / FR-017 interview artefacts unless explicitly requested.
