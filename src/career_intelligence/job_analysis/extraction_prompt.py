"""Compact extraction instructions for the OpenAI job-analysis extractor."""

EXTRACTION_PROMPT_VERSION = "v5"

EXTRACTION_INSTRUCTIONS_V1 = """
You extract a structured Job Analysis from one complete job posting.

Input sections (trusted caller metadata + description):
- <JobTitle> — role title when supplied
- <Company> — employer when supplied
- <SourceURL> — listing URL when supplied (provenance only; do not invent facts from it)
- <JobDescription> — job description body

Analyse the entire posting. Do not ignore JobTitle, Company, or other tagged metadata.

Evidence (global — applies to every section):
- Every non-unknown / non-unspecified / non-unstated claim MUST include at least one
  exact supporting excerpt from the tagged posting, with the correct provenance section
  (use "Job title" for title evidence).
- Never emit a known role family, technology, responsibility, experience requirement,
  seniority, location, work arrangement, compensation, or employment value with
  evidence=[].
- If you cannot quote supporting evidence, do not make the claim (use unknown /
  unspecified / unstated instead).

Rules:
- Analyse only the supplied posting. Do not compare it to a candidate or career profile.
- Do not recommend apply, skip, tier, or effort. Do not assess candidate fit.
- Distinguish required vs preferred vs unspecified for technologies and experience.
- Never invent compensation, seniority, role family, employment, or other missing facts.
- Emit exactly the JobAnalysisExtraction schema. Never emit a posting field.
- Responsibilities and technologies come primarily from <JobDescription>.

Seniority:
- Prefer a clear seniority signal in <JobTitle> (e.g. Principal, Senior, Lead, Mid, Junior)
  over inferring seniority from the body alone.
- If the title clearly states one level and the body does not conflict: use that level,
  ambiguous=false, and cite the title excerpt with section="Job title".
- If the posting states no seniority information anywhere: level="unknown",
  ambiguous=false, candidate_levels=[], evidence=[].
- Set ambiguous=true only when title and/or body support conflicting or multiple
  plausible non-unknown levels. Then level="unknown", candidate_levels lists those
  levels, and evidence cites each conflicting excerpt.
- Do not set ambiguous=true merely because seniority is missing or uncertain.

Compensation:
- If no compensation is stated: clarity="unstated", minimum=null, maximum=null,
  currency=null, period=null, raw_text=null, evidence=[].
- Do not put "competitive", interview-only, or similar wording into raw_text or evidence
  when clarity is "unstated".
- Use clarity="stated" or "ambiguous" only when the posting actually provides amount,
  range, rate, or other compensation content — with evidence excerpts.

Employment (never infer; keep strict):
- working_hours and engagement_type are independent. Populate each only when the posting
  explicitly states that dimension. Otherwise leave it "unspecified".
- Known employment values require evidence (same global rule). If employment is fully
  unspecified, evidence must be [].
- Explicit positives: "full-time"/"full time" → full_time; "part-time"/"part time" →
  part_time; "permanent" → permanent; "contract"/"contractor" → contract; "casual" →
  casual; "fixed-term"/"temporary" (fixed term) → fixed_term; "internship"/"intern" →
  internship.
- Do NOT set employment from: "join our team", "opportunity", "you'll work", "in-office",
  "hybrid", "office based", benefits, recruiter tone, seniority, or company description.
- Examples: "Full-time permanent role" → both dimensions set with evidence; "6 month
  contract" → engagement_type=contract with evidence; "Part-time" → working_hours=
  part_time with evidence; Principal title or "junior-to-mid"/"in-office" alone →
  both unspecified, evidence=[].
""".strip()
