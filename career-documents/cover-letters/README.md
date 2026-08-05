# Cover letters

FR-007 cover letter drafts for owner review.

- `generated/` — Markdown, HTML, PDF, CoverLetter JSON, and plan JSON
  (path is covered by `career-documents/**/generated/` in `.gitignore`)
- Do not submit or email without owner review
- Generate with `scripts/run_cover_letter_manual.py` (or FR-010/FR-011 package paths)
- Owner edits belong in **Markdown only** — then refresh HTML/PDF with
  `python scripts/render_document.py --markdown <path>` (render-only; no planner
  or composer). See [docs/08_implementation_notes.md](../docs/08_implementation_notes.md)
  § Document Rendering
