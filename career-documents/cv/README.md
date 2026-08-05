# Career documents — CV

## Canonical Master CV

| Artefact | Path |
|----------|------|
| Markdown | [`master_ai_engineer_cv.md`](master_ai_engineer_cv.md) |
| HTML (preferred PDF source) | [`master_ai_engineer_cv.html`](master_ai_engineer_cv.html) |
| PDF | [`master_ai_engineer_cv.pdf`](master_ai_engineer_cv.pdf) |

This is the frozen **Master CV v4** content baseline for future tailored CV generation.

**Presentation:** Shared print CSS lives in
`src/career_intelligence/cv_generation/assets/cv_print.css` and is the design
source for both the Master HTML and FR-006 tailored HTML. Sync into the Master
file with:

```bash
python scripts/sync_master_cv_css.py
python scripts/sync_master_cv_css.py --check
```

Layout benchmark is the archived Master CV **v3** PDF (readability / spacing).
Current Master **content** remains authoritative. Prefer readability over
minimum page count; ≈4–5 pages is acceptable when content warrants it.

Update content only when driven by new portfolio projects, certifications,
recruiter/interview feedback, or measurable application outcomes.

## Other folders

- `generated/` — tailored CVs from FR-006 (plan JSON, CV JSON, Markdown, standalone HTML, PDF)
- After owner Markdown edits, refresh HTML/PDF with
  `python scripts/render_document.py --markdown <path>` (do not edit HTML/PDF as source)
- `archive/` — superseded Master CV versions
