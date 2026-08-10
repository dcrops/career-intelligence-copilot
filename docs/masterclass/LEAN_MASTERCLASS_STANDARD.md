# Lean Masterclass Standard

**Status:** Permanent Engineering Learning Academy standard  
**Validated by:** FR-016 and FR-017 Lean Masterclasses  
**Scope:** All future Engineering Masterclasses generated from Masterclass Source Packages  
**Not this document:** Packaging rules for `sources/` snapshots — see [PACKAGING.md](PACKAGING.md)

---

## Philosophy

Teach the engineering. Do **not** reproduce repository documentation.

Lean Edition target: **approximately 8–12 pages**. Prefer interview-ready narrative over textbook completeness. Do not inflate size when adding required sections.

Canonical engineering remains acceptance reports and ADRs. The Masterclass is the
**deep learning** educational artefact:

```text
Lean Masterclass (Markdown) → Masterclass PDF
  → Gamma Learning Presentation (15–20 slides)
  → Interview Brief (1 page) → Interview Deck (3–5 slides)
  → Interview Revision / Coaching
```

The **PDF is a mandatory Academy artefact** (official study edition). It must
faithfully render the Markdown — no engineering rewrite.

Render with:

```powershell
# Entire package (Lean Masterclass + sources/ + sources/optional/)
python scripts/render_masterclass_pdf.py --package FRnnn

# Or via package builder (snapshots + PDFs)
python scripts/build_masterclass_package.py FRnnn

# Single Lean Masterclass file
python scripts/render_masterclass_pdf.py docs/masterclass/FRnnn/Engineering_Masterclass_00N_FRnnn.md
```

Source and optional milestone snapshots also receive sibling PDFs as part of the
same automatic packaging step — see [PACKAGING.md](PACKAGING.md).

Rapid interview revision (Brief + Deck) is defined separately — see Related. This
Lean Masterclass standard is **not** shortened or replaced by those artefacts.
---

## Required teaching spine

Every Lean Masterclass must cover:

1. The engineering problem  
2. Why previous approaches were insufficient  
3. The chosen architecture  
4. The engineering principles  
5. The validation  
6. The trade-offs  
7. Interview preparation  
8. Three engineering lessons to remember  

---

## Permanent required sections (post FR-017)

These sections are **mandatory** for every future Masterclass. Keep each short.

### 1. Runtime Example

Include **one** simple engineering runtime flow.

| Requirement | Detail |
|-------------|--------|
| Count | Exactly one primary flow |
| Style | Conceptual, engineering-focused |
| Detail level | No implementation detail (no APIs, file paths, class names unless essential to the idea) |
| Purpose | Give Gamma a deterministic flow that becomes a diagram easily |

Present as a short prose step list or a compact text flow diagram. Examples vary by Functional Requirement (orchestration, evaluation, preparation, truth gates, etc.).

### 2. Why Employers Care

Include a short section explaining why this engineering work would matter to an employer.

| Do | Do not |
|----|--------|
| Transferable engineering capability | Salary, recruiting, or marketing language |
| Engineering value (safety, clarity, cost of wrong metrics, authority boundaries, …) | Product pitch or employment guarantees |

### 3. Validation Summary

Include a **compact** validation summary suitable for Gamma callout boxes.

Typical contents (keep terse):

- major validation outcome  
- important test / corpus counts  
- overall recommendation  
- important constraints  

Do not paste full test matrices here — the Validation teaching section may expand briefly afterward.

### 4. Memorable Closing Statement

End with **one** concise engineering takeaway.

| Requirement | Detail |
|-------------|--------|
| Length | One sentence (optionally one short supporting line) |
| Content | Summarises the engineering philosophy demonstrated |
| Purpose | Memorable enough to become the final Gamma slide |

Place this **after** “Three engineering lessons,” as the final substantive close.

---

## Size discipline

Adding the four permanent sections must **not** push the Masterclass into textbook length. Prefer cutting redundant prose elsewhere over expanding these boxes.

---

## Generation contract

When generating a Masterclass:

1. Attach the FR’s `docs/masterclass/FRnnn/` package.  
2. Follow [MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md).  
3. Satisfy this standard (spine + permanent sections).  
4. Do not generate slides, presentation notes, or image prompts unless explicitly requested.  
5. Do not contradict the FR’s acceptance report or ADRs.  
6. After the Markdown Masterclass is complete, render package PDFs (Lean study
   edition **plus** `sources/` and `sources/optional/` siblings) via
   `scripts/build_masterclass_package.py` or
   `scripts/render_masterclass_pdf.py --package FRnnn` before Gamma.
7. After the Gamma Learning Presentation, produce Interview Brief + Interview Deck
   per [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) and
   [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md) (do not turn them into
   another Masterclass).

---

## Related

| Document | Role |
|----------|------|
| [README.md](README.md) | Academy index and workflow |
| [MASTERCLASS_GENERATOR_LEAN.md](MASTERCLASS_GENERATOR_LEAN.md) | Lean Edition generator prompt |
| [PACKAGING.md](PACKAGING.md) | Source-package snapshot rules |
| `scripts/render_masterclass_pdf.py` | Markdown → PDF (single file or `--package`) |
| `scripts/build_masterclass_package.py` | Snapshots + automatic sibling PDFs |
| [INTERVIEW_BRIEF_STANDARD.md](INTERVIEW_BRIEF_STANDARD.md) | Rapid text revision (~1 page) |
| [INTERVIEW_DECK_STANDARD.md](INTERVIEW_DECK_STANDARD.md) | Rapid visual revision (~3–5 slides) |
