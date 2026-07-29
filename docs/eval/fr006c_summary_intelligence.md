# FR-006c — Summary Intelligence

**Status:** Final polish implemented (ready for owner close)  
**Date:** 2026-07-29

## Purpose

Deterministic Phase B Professional Summary composition that equals the Master /
manual Shield recruiter bar: credibility-first personal brand, natural story,
scannable bold, and evidence-only claims. Phase C OpenAI rewrite remains opt-in.

## Story structure

| Paragraph | Intent | Stability |
|-----------|--------|-----------|
| 1 | Why interview — commercial DE years, independent portfolio, end-to-end systems | Stable personal brand |
| 2 | What they build — job-relevant tech; one primary theme promoted once | Role-tailored |
| 3 | How they engineer — AI Engineering methodology | Stable (profile-grounded) |
| 4 | Value — traceable outputs for operational decision-making | Stable close |

## Pipeline

```
Career Profile summary + Tailoring Plan themes/skills
        ↓
Gather evidence (years, portfolio, tech focus, single primary theme)
        ↓
Compose who / what / how / value
        ↓
Bold years + tech + key concepts (first occurrence)
        ↓
Grounding checks
        ↓
summary_source = theme_aware_composition
```

Module: `src/career_intelligence/cv_generation/summary_intelligence.py`

## Final polish sample (Allura / backend)

> AI Engineer with **3.5 years of commercial enterprise Data Engineering**
> experience and an independent AI Engineering portfolio across retrieval
> systems, operational intelligence, explainable AI, and enterprise decision
> support. Builds **end-to-end AI applications** with **software engineering
> discipline**.
>
> Designs and delivers these systems with **Python**, **REST APIs**, and
> **FastAPI**, applying modern **AI engineering practices** — with emphasis on
> **Operational intelligence**.
>
> Applies a disciplined **AI Engineering methodology** — **architecture-first**
> design, **evidence-based validation**, and **human-in-the-loop** review — to
> deliver AI systems with traceable, reviewable outputs.
>
> Focused on engineering AI systems with traceable, reviewable outputs for
> operational decision-making.

Platform (Maincode), governance (Forever New), and production AI (Bluefin)
share the identical opening brand paragraph (including bold markers); paragraph
2 tech/theme adapts per role.

## Engineering Highlights

`select_engineering_highlights` keeps the curated portfolio-impact lead bullet
first; remaining profile bullets are relevance-ordered. No invented text.

## Validation

- Unit: `tests/unit/cv_generation/test_summary_intelligence.py`,
  `test_content_selection.py`
- Manual (2026-07-29): Allura (backend), Maincode (platform), Forever New
  (governance / governed agents), Bluefin (production AI systems)
