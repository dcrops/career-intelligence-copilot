# Document Positioning M2 — Four-job capability inspection

Inspection artefact only. Not production document generation. Not an M5 A/B evaluation. PositioningPlan is still **not** wired into `cic package prepare`.

Shared candidate evidence: `data/career_profile.yaml`.

TailoringPlan classifications use the same catalogue as PositioningPlan.

# E1 — Allura AI Engineer (control)

## Top employer needs

1. **Python** (technology, required) → `supported_direct`
2. **Google Cloud** (technology, preferred) → `unsupported`
3. **REST APIs** (technology, required) → `supported_direct`
4. **LLM** (technology, required) → `supported_direct`
5. **MLOps** (technology, preferred) → `unsupported`
6. **DevOps** (technology, preferred) → `unsupported`
7. **data pipelines** (responsibility) → `supported_related`

## DIRECT requirements

- **Python** — promote `Python` (skill:Python, experience:chase-risk-compliance-ai-engineer, experience:nbn-data-engineer-2020)
- **REST APIs** — promote `REST APIs` (skill:REST APIs, project:public-holiday-entitlements)
- **LLM** — promote `LLM application development` (skill:LLM application development, experience:ai-engineering-development-2025)

## RELATED requirements

- **data pipelines** — promote `Azure Data Factory` (skill:Azure Data Factory, experience:data-engineering-development-2023)

## UNSUPPORTED requirements

- **Google Cloud** (no evidence refs)
- **MLOps** (no evidence refs)
- **DevOps** (no evidence refs)

## Selected evidence

- `skill:Python` (skill)
- `experience:chase-risk-compliance-ai-engineer` (experience)
- `experience:nbn-data-engineer-2020` (experience)
- `skill:REST APIs` (skill)
- `project:public-holiday-entitlements` (project)
- `skill:LLM application development` (skill)
- `experience:ai-engineering-development-2025` (experience)
- `skill:Azure Data Factory` (skill)
- `experience:data-engineering-development-2023` (experience)

## Argument spine

- **direct:** Claim 'Python' as a candidate capability via profile evidence 'Python'.
- **gap:** Gap: 'Google Cloud' is unsupported by CareerProfile evidence and must not be claimed.
- **direct:** Claim 'REST APIs' as a candidate capability via profile evidence 'REST APIs'.
- **direct:** Claim 'LLM' as a candidate capability via profile evidence 'LLM application development'.
- **gap:** Gap: 'MLOps' is unsupported by CareerProfile evidence and must not be claimed.
- **gap:** Gap: 'DevOps' is unsupported by CareerProfile evidence and must not be claimed.
- **related:** Do not claim 'data pipelines'. Promote 'Azure Data Factory' as related candidate evidence for this employer need.
- **trajectory:** Trajectory mode is ai_lead. Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **portfolio:** Use portfolio project 'Public Holiday Entitlements Application' as packed evidence; keep Master project body unchanged.
- **portfolio:** Use portfolio project 'Career Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.
- **portfolio:** Use portfolio project 'Operational Intelligence Copilot' as packed evidence; keep Master project body unchanged. Do not treat this project as evidence for unsupported employer technologies.

## Forbidden claims

- Must not claim **Google Cloud** (unsupported; requested 'Google Cloud')
- Must not claim **MLOps** (unsupported; requested 'MLOps')
- Must not claim **DevOps** (unsupported; requested 'DevOps')
- Must not claim **data pipelines** (related_unclaimable; requested 'data pipelines')
- Must not claim **data pipeline** (related_unclaimable; requested 'data pipelines')
- Must not claim **etl** (related_unclaimable; requested 'data pipelines')

## Trajectory and methodology

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.

## Rewrite authority

- CV rewrite surface: professional_summary, selected_engineering_highlights, optional_project_relevance_line, skills_emphasis
- Locked Master sections: experience_headings_dates_relationship, experience_bullets, project_bodies, courses, certifications, contact

### TailoringPlan technology classifications

| Requested | Planner support | Identity | Promoted profile evidence | may_claim_requested |
|---|---|---|---|---|
| Python | DIRECT | — | Python | True |
| REST APIs | DIRECT | rest | REST APIs | True |
| LLM | DIRECT | llm | LLM application development | True |
| Google Cloud | UNSUPPORTED | — | — | False |
| MLOps | UNSUPPORTED | — | — | False |
| DevOps | UNSUPPORTED | — | — | False |

**skills_to_promote:** Python, REST APIs, FastAPI, OpenAI APIs

## Why this positioning differs

Python and REST APIs remain DIRECT. LLM is now DIRECT via CareerProfile skill `LLM application development` (not a RAG shortcut). Google Cloud / MLOps / DevOps stay honest gaps.

### Shared-technology agreement

PositioningPlan and TailoringPlan agree on every shared JobAnalysis technology.

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

### TailoringPlan technology classifications

| Requested | Planner support | Identity | Promoted profile evidence | may_claim_requested |
|---|---|---|---|---|
| AWS Bedrock | RELATED | aws_bedrock | AWS | False |
| Python | DIRECT | — | Python | True |
| RAG | DIRECT | rag | Retrieval-Augmented Generation | True |

**skills_to_promote:** AWS, Python, Retrieval-Augmented Generation, FastAPI

## Why this positioning differs

RAG DIRECT. AWS Bedrock RELATED via AWS (`may_claim_requested=False`). Chatbot/conversational AI remains UNSUPPORTED. Bedrock is not a promoted candidate skill.

### Shared-technology agreement

PositioningPlan and TailoringPlan agree on every shared JobAnalysis technology.

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

### TailoringPlan technology classifications

| Requested | Planner support | Identity | Promoted profile evidence | may_claim_requested |
|---|---|---|---|---|
| GPU | UNSUPPORTED | — | — | False |
| Linux | UNSUPPORTED | — | — | False |
| HPC | UNSUPPORTED | — | — | False |

**skills_to_promote:** Python, FastAPI, OpenAI APIs, Retrieval-Augmented Generation

## Why this positioning differs

GPU/Linux/HPC stay UNSUPPORTED. No infrastructure invention.

### Shared-technology agreement

PositioningPlan and TailoringPlan agree on every shared JobAnalysis technology.

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

### TailoringPlan technology classifications

| Requested | Planner support | Identity | Promoted profile evidence | may_claim_requested |
|---|---|---|---|---|
| AI tools | UNSUPPORTED | — | — | False |
| Copilot | UNSUPPORTED | — | — | False |
| Claude | UNSUPPORTED | — | — | False |

**skills_to_promote:** Operational intelligence, Explainable AI, Enterprise decision support, Human-in-the-loop validation

## Why this positioning differs

Copilot/Claude remain unclaimed unless evidenced. QA→DE→AI trajectory is unchanged (`full_chapters` on PositioningPlan).

### Shared-technology agreement

PositioningPlan and TailoringPlan agree on every shared JobAnalysis technology.

---

# Cross-job contrast

- E1 vs M1: LLM is now DIRECT because the profile skill `LLM application development` resolves to identity `llm`. RAG is a different identity and is not used as a shortcut.
- E2: Bedrock stays RELATED; chatbot stays a gap. Correct gaps are success, not extra green matches.
- E3: infrastructure asks remain unsupported.
- E4: trajectory_mode remains `full_chapters`.
