# Document Positioning M1 — Four-job PositioningPlan inspection

Inspection artefact only. Not production document generation. Not an M5 A/B evaluation.

Shared candidate evidence: `data/career_profile.yaml`.

# E1 — Allura AI Engineer (control)

## Top employer needs

1. **Python** (technology, required) → `supported_direct`
2. **Google Cloud** (technology, preferred) → `unsupported`
3. **REST APIs** (technology, required) → `supported_direct`
4. **LLM** (technology, required) → `unsupported`
5. **MLOps** (technology, preferred) → `unsupported`
6. **DevOps** (technology, preferred) → `unsupported`

## DIRECT requirements

- **Python** — promote `Python` (skill:Python, experience:chase-risk-compliance-ai-engineer, experience:nbn-data-engineer-2020)
- **REST APIs** — promote `REST APIs` (skill:REST APIs, project:public-holiday-entitlements)

## RELATED requirements

- None

## UNSUPPORTED requirements

- **Google Cloud** (no evidence refs)
- **LLM** (no evidence refs)
- **MLOps** (no evidence refs)
- **DevOps** (no evidence refs)

## Selected evidence

- `skill:Python` (skill)
- `experience:chase-risk-compliance-ai-engineer` (experience)
- `experience:nbn-data-engineer-2020` (experience)
- `skill:REST APIs` (skill)
- `project:public-holiday-entitlements` (project)

## Argument spine

- **direct:** Claim 'Python' as a candidate capability via profile evidence 'Python'.
- **gap:** Gap: 'Google Cloud' is unsupported by CareerProfile evidence and must not be claimed.
- **direct:** Claim 'REST APIs' as a candidate capability via profile evidence 'REST APIs'.
- **gap:** Gap: 'LLM' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'MLOps' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'DevOps' is unsupported by CareerProfile evidence and must not be claimed.
- **trajectory:** Trajectory mode is ai_lead. Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **portfolio:** Use portfolio project 'Public Holiday Entitlements Application' as packed evidence; keep Master project body unchanged.
- **portfolio:** Use portfolio project 'Career Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Operational Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.

## Forbidden claims

- Must not claim **Google Cloud** (unsupported; requested 'Google Cloud')
- Must not claim **LLM** (unsupported; requested 'LLM')
- Must not claim **MLOps** (unsupported; requested 'MLOps')
- Must not claim **DevOps** (unsupported; requested 'DevOps')

## Trajectory and methodology

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.

## Rewrite authority

- CV rewrite surface: professional_summary, selected_engineering_highlights, optional_project_relevance_line, skills_emphasis
- Locked Master sections: experience_headings_dates_relationship, experience_bullets, project_bodies, courses, certifications, contact

## Why this positioning differs

Applied AI Engineer control: DIRECT Python and REST APIs, `ai_lead` trajectory, methodology on because evaluation/governance appear in structured responsibilities. LLM/MLOps/GCP remain UNSUPPORTED unknown labels (catalogue v1 does not alias LLM → RAG).

---

# E2 — CSK mixed-fit specialist

## Top employer needs

1. **AWS Bedrock** (technology, required) → `supported_related`
2. **Python** (technology, required) → `supported_direct`
3. **RAG** (technology, required) → `supported_direct`
4. **conversational ai** (experience_requirement, required) → `unsupported`

## DIRECT requirements

- **Python** — promote `Python` (skill:Python, experience:chase-risk-compliance-ai-engineer, experience:nbn-data-engineer-2020)
- **RAG** — promote `Retrieval-Augmented Generation` (skill:Retrieval-Augmented Generation, project:governance-document-rag)

## RELATED requirements

- **AWS Bedrock** — promote `AWS` (skill:AWS, experience:nbn-data-engineer-2020, certification:aws-certified-developer-associate)

## UNSUPPORTED requirements

- **conversational ai** (no evidence refs)

## Selected evidence

- `skill:AWS` (skill)
- `experience:nbn-data-engineer-2020` (experience)
- `certification:aws-certified-developer-associate` (certification)
- `skill:Python` (skill)
- `experience:chase-risk-compliance-ai-engineer` (experience)
- `skill:Retrieval-Augmented Generation` (skill)
- `project:governance-document-rag` (project)

## Argument spine

- **related:** Do not claim 'AWS Bedrock'. Promote 'AWS' as related candidate evidence for this employer need.
- **direct:** Claim 'Python' as a candidate capability via profile evidence 'Python'.
- **direct:** Claim 'RAG' as a candidate capability via profile evidence 'Retrieval-Augmented Generation'.
- **gap:** Gap: 'conversational ai' is unsupported by CareerProfile evidence and must not be claimed.
- **trajectory:** Trajectory mode is ai_lead. Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **portfolio:** Use portfolio project 'Governance-Aware Document Intelligence RAG' as packed evidence; keep Master project body unchanged.
- **portfolio:** Use portfolio project 'Career Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Operational Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.

## Forbidden claims

- Must not claim **AWS Bedrock** (related_unclaimable; requested 'AWS Bedrock')
- Must not claim **amazon bedrock** (related_unclaimable; requested 'AWS Bedrock')
- Must not claim **bedrock** (related_unclaimable; requested 'AWS Bedrock')
- Must not claim **conversational ai** (unsupported; requested 'conversational ai')
- Must not claim **customer support automation** (unsupported; requested 'conversational ai')
- Must not claim **customer support agents** (unsupported; requested 'conversational ai')
- Must not claim **conversational interfaces** (unsupported; requested 'conversational ai')
- Must not claim **virtual agents** (unsupported; requested 'conversational ai')
- Must not claim **chatbots** (unsupported; requested 'conversational ai')
- Must not claim **chatbot** (unsupported; requested 'conversational ai')

## Trajectory and methodology

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.

## Rewrite authority

- CV rewrite surface: professional_summary, selected_engineering_highlights, optional_project_relevance_line, skills_emphasis
- Locked Master sections: experience_headings_dates_relationship, experience_bullets, project_bodies, courses, certifications, contact

## Why this positioning differs

Mixed-fit specialist: AWS Bedrock is RELATED (promote AWS, forbid Bedrock experience), RAG is DIRECT via Retrieval-Augmented Generation, chatbot/conversational AI is an honest gap. Same `ai_lead` family as E1, but the transfer argument is the point.

---

# E3 — Maincode AI Infrastructure Engineer

## Top employer needs

1. **GPU** (technology, required) → `unsupported`
2. **Linux** (technology, required) → `unsupported`
3. **HPC** (technology, preferred) → `unsupported`

## DIRECT requirements

- None

## RELATED requirements

- None

## UNSUPPORTED requirements

- **GPU** (no evidence refs)
- **Linux** (no evidence refs)
- **HPC** (no evidence refs)

## Selected evidence

- None

## Argument spine

- **gap:** Gap: 'GPU' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'Linux' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'HPC' is unsupported by CareerProfile evidence and must not be claimed.
- **trajectory:** Trajectory mode is ai_lead. Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **portfolio:** Use portfolio project 'Career Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Operational Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Governance-Aware Document Intelligence RAG' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.

## Forbidden claims

- Must not claim **GPU** (unsupported; requested 'GPU')
- Must not claim **Linux** (unsupported; requested 'Linux')
- Must not claim **HPC** (unsupported; requested 'HPC')

## Trajectory and methodology

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **include_methodology:** `False`
- Structured employer needs do not invoke evaluation, orchestration, governance, or equivalent methodology signals.

## Rewrite authority

- CV rewrite surface: professional_summary, selected_engineering_highlights, optional_project_relevance_line, skills_emphasis
- Locked Master sections: experience_headings_dates_relationship, experience_bullets, project_bodies, courses, certifications, contact

## Why this positioning differs

Infra stretch: GPU/Linux/HPC stay UNSUPPORTED with no fabricated employment. Methodology omitted (no evaluation/governance needs). Portfolio is packed as candidate evidence only — not as GPU proof.

---

# E4 — Repurpose AI Adoption Specialist

## Top employer needs

1. **AI tools** (technology, required) → `unsupported`
2. **Copilot** (technology, required) → `unsupported`
3. **Claude** (technology, required) → `unsupported`

## DIRECT requirements

- None

## RELATED requirements

- None

## UNSUPPORTED requirements

- **AI tools** (no evidence refs)
- **Copilot** (no evidence refs)
- **Claude** (no evidence refs)

## Selected evidence

- None

## Argument spine

- **gap:** Gap: 'AI tools' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'Copilot' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'Claude' is unsupported by CareerProfile evidence and must not be claimed.
- **trajectory:** Trajectory mode is full_chapters. Role family is AI-adjacent and the profile has testing, data-engineering, and independent AI chapters, so the career trajectory is the hiring argument.
- **portfolio:** Use portfolio project 'Career Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Operational Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Governance-Aware Document Intelligence RAG' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.

## Forbidden claims

- Must not claim **AI tools** (unsupported; requested 'AI tools')
- Must not claim **Copilot** (unsupported; requested 'Copilot')
- Must not claim **Claude** (unsupported; requested 'Claude')

## Trajectory and methodology

- **trajectory_mode:** `full_chapters`
- Role family is AI-adjacent and the profile has testing, data-engineering, and independent AI chapters, so the career trajectory is the hiring argument.
- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.

## Rewrite authority

- CV rewrite surface: professional_summary, selected_engineering_highlights, optional_project_relevance_line, skills_emphasis
- Locked Master sections: experience_headings_dates_relationship, experience_bullets, project_bodies, courses, certifications, contact

## Why this positioning differs

AI-adjacent adoption role: Copilot/Claude/AI tools are not claimed. `full_chapters` trajectory is the hiring argument (QA → DE → independent AI). Methodology on via risk-management wording.

---

# Cross-job contrast

- E1 vs E2: both `ai_lead`, but E2 is the only RELATED/Bedrock transfer case and the only chatbot gap.
- E3 vs E1: same role family, but E3 has no DIRECT technologies and omits methodology — an honest stretch, not a skill dump.
- E4 vs E1–E3: only `full_chapters`, because `role_family` is `ai_adjacent` and the profile has testing + DE + independent AI.
