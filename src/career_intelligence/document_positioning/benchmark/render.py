"""Owner-facing blind comparison artefacts. No generator identity."""

from __future__ import annotations

import re
from pathlib import Path

from career_intelligence.document_positioning.benchmark.evidence import FactualEvidenceBundle
from career_intelligence.document_positioning.benchmark.jobs import FrozenEvalJob
from career_intelligence.document_positioning.benchmark.mapping import BlindMapping
from career_intelligence.document_positioning.benchmark.protocol import (
    OWNER_CHROME_LEAK_TOKENS,
    RUBRIC_DIMENSIONS,
)

_CIC_FOOTER = re.compile(
    r"\n---\s*\n\*M4 positioned cover letter[^*]*\*\s*$",
    re.IGNORECASE,
)
_CANONICAL_FOOTER = re.compile(
    r"(?:\n---\s*)?(?:\n\*Canonical Master CV[^*]*\*)?\s*$",
    re.IGNORECASE,
)

DIMENSION_LABELS = {
    "scan_15s": "15-second scan",
    "role_positioning": "Role positioning",
    "evidence_selection": "Evidence selection",
    "transfer_argument": "Transfer argument",
    "honest_gaps": "Honest gaps",
    "specificity": "Specificity",
    "clarity": "Clarity",
    "concision": "Concision",
    "overall_submit_preference": "Overall submit preference",
}

OWNER_INSTRUCTIONS = """# M5 blind comparison — owner instructions

Score the documents **without** trying to guess which generator produced them.

For each job folder:

1. Read `job_context.md`.
2. Spend about 15 seconds on Version A’s CV, then on Version B’s CV.
   Note what the candidate appears to be, and why they seem relevant.
3. Compare CV vs CV, then cover letter vs cover letter.
   Use `comparison.md` or the separate Version files.
4. Fill `scoring_sheet.md` **and** the shared `owner_scores.json`.

For every rubric row choose exactly one of:

- Version A preferred
- Version B preferred
- Tie

The **overall submit preference** is your decision. Do not let anyone
derive it automatically from the other rows.

Do not open `../hidden/`. That directory identifies the generators.

When all four jobs are scored, return `owner_scores.json` (and any notes
in the scoring sheets). The mapping will be revealed only after that.
"""


def sanitize_owner_markdown(markdown: str) -> str:
    cleaned = _CIC_FOOTER.sub("", markdown)
    cleaned = _CANONICAL_FOOTER.sub("", cleaned)
    return cleaned.strip() + "\n"


def chrome_leak_hits(text: str) -> list[str]:
    folded = text.casefold()
    return [token for token in OWNER_CHROME_LEAK_TOKENS if token in folded]


def write_owner_review(
    *,
    owner_dir: Path,
    jobs: tuple[FrozenEvalJob, ...],
    bundles: dict[str, FactualEvidenceBundle],
    mapping: BlindMapping,
    documents: dict[str, dict[str, tuple[str, str]]],
) -> None:
    """Write owner artefacts.

    ``documents`` maps job_id -> system -> (cv_markdown, letter_markdown).
    """
    owner_dir.mkdir(parents=True, exist_ok=True)
    (owner_dir / "README.md").write_text(OWNER_INSTRUCTIONS, encoding="utf-8")
    scores: dict[str, object] = {}
    for job in jobs:
        bundle = bundles[job.job_id]
        assignment = mapping.assignment(job.job_id)
        pair = documents[job.job_id]
        version_docs = {
            "A": pair[assignment.version_a],
            "B": pair[assignment.version_b],
        }
        job_dir = owner_dir / f"{job.job_id}_{_slug(job.name)}"
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "job_context.md").write_text(
            _job_context(job, bundle), encoding="utf-8"
        )
        (job_dir / "version_a_cv.md").write_text(
            sanitize_owner_markdown(version_docs["A"][0]), encoding="utf-8"
        )
        (job_dir / "version_a_letter.md").write_text(
            sanitize_owner_markdown(version_docs["A"][1]), encoding="utf-8"
        )
        (job_dir / "version_b_cv.md").write_text(
            sanitize_owner_markdown(version_docs["B"][0]), encoding="utf-8"
        )
        (job_dir / "version_b_letter.md").write_text(
            sanitize_owner_markdown(version_docs["B"][1]), encoding="utf-8"
        )
        (job_dir / "comparison.md").write_text(
            _comparison_markdown(job, bundle, version_docs),
            encoding="utf-8",
        )
        (job_dir / "scoring_sheet.md").write_text(
            _scoring_sheet(job), encoding="utf-8"
        )
        scores[job.job_id] = {
            "job_id": job.job_id,
            "job_name": job.name,
            "overall": None,
            "dimensions": {key: None for key in RUBRIC_DIMENSIONS},
            "notes": {
                "scan_15s_version_a": "",
                "scan_15s_version_b": "",
                "other": "",
            },
        }
    import json

    (owner_dir / "owner_scores.json").write_text(
        json.dumps(scores, indent=2) + "\n",
        encoding="utf-8",
    )


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")


def _job_context(job: FrozenEvalJob, bundle: FactualEvidenceBundle) -> str:
    needs = "\n".join(
        f"- {item.label} ({item.kind})"
        for item in bundle.employer_needs[:16]
    )
    return (
        f"# {job.job_id} — {job.name}\n\n"
        f"**Company:** {bundle.company}  \n"
        f"**Role title:** {bundle.role_title}  \n"
        f"**Role family:** {bundle.role_family.replace('_', ' ')}\n\n"
        "Judge both versions against this role. Generator identity is not "
        "included on purpose.\n\n"
        "## Employer needs (from the frozen job analysis)\n\n"
        f"{needs}\n\n"
        "## Advertisement (frozen verbatim)\n\n"
        f"{bundle.advertisement_text.strip()}\n"
    )


def _comparison_markdown(
    job: FrozenEvalJob,
    bundle: FactualEvidenceBundle,
    version_docs: dict[str, tuple[str, str]],
) -> str:
    a_cv = sanitize_owner_markdown(version_docs["A"][0]).strip()
    b_cv = sanitize_owner_markdown(version_docs["B"][0]).strip()
    a_letter = sanitize_owner_markdown(version_docs["A"][1]).strip()
    b_letter = sanitize_owner_markdown(version_docs["B"][1]).strip()
    return (
        f"# {job.job_id} comparison — {bundle.company} / {bundle.role_title}\n\n"
        "Generator identity is withheld. Score Version A against Version B.\n\n"
        "## Version A — CV\n\n"
        f"{a_cv}\n\n"
        "---\n\n"
        "## Version B — CV\n\n"
        f"{b_cv}\n\n"
        "---\n\n"
        "## Version A — cover letter\n\n"
        f"{a_letter}\n\n"
        "---\n\n"
        "## Version B — cover letter\n\n"
        f"{b_letter}\n"
    )


def _scoring_sheet(job: FrozenEvalJob) -> str:
    rows = []
    for key in RUBRIC_DIMENSIONS:
        label = DIMENSION_LABELS[key]
        rows.append(
            f"### {label}\n\n"
            "- [ ] Version A preferred\n"
            "- [ ] Version B preferred\n"
            "- [ ] Tie\n"
        )
    return (
        f"# {job.job_id} scoring sheet — {job.name}\n\n"
        "Choose one option per row. The overall submit preference is the job result.\n\n"
        + "\n".join(rows)
        + "\n## 15-second scan notes\n\n"
        "**Version A:**\n\n\n"
        "**Version B:**\n\n\n"
        "## Other notes\n\n"
    )
