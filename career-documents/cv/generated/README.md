# Generated tailored CV drafts (FR-006)

Owner-review drafts written by `scripts/run_cv_generation_manual.py` and
`career_intelligence.cv_generation.write_tailored_cv_drafts`.

**FR-006 status:** Complete. Drafts may use profile-summary copy
(`summary_source=profile_copy`) or optional OpenAI rewrite
(`--rewrite-summary` → `openai_rewrite` / `fallback_profile_copy`).

Each run typically produces:

- `{stem}.tailoring_plan.json`
- `{stem}.json` (TailoredCv)
- `{stem}.md` (Markdown)

Do not submit or email drafts without owner review. No PDF/DOCX in this folder.
