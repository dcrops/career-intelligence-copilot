from __future__ import annotations

import truststore

truststore.inject_into_ssl()

import json

from career_intelligence.job_analysis import JobAnalysisService, JobPosting
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor


JOB_TEXT = """
Software Engineer (AI)

Jonas Software Australia 
View all jobs
Cremorne, Melbourne VIC (Hybrid)
Developers/Programmers (Information & Communication Technology)
Full time
About Us
The Jonas Software Group acquires, manages, and builds industry-specific software companies globally. With 100+ companies and 2,500+ employees, our people are at the core of everything we do.

The Caudex Group is a Melbourne-based technology company building a portfolio of purpose-built software products for Australian industries. We’re a small, ambitious team with a broad remit – multiple products, fast cycles, and a genuine commitment to building software the modern way. If you want to work somewhere your output ships quickly and your ideas get heard, this is it.



About the Role
We’re looking for a Software Engineer (AI) who genuinely loves working with AI—not as a buzzword, but as a core part of how you build, think, and solve problems.

This is a junior-to-mid level opportunity (2–5 years’ experience) where you’ll work across multiple products, contributing end-to-end and shipping quickly in a highly collaborative, in-office environment. You’ll be part of a small product team shaping how modern, AI-first software gets built at Caudex.



Key responsibilities include:
Contributing across multiple product initiatives, adapting to shifting priorities and fast delivery cycles.

Building full stack features end-to-end, including front-end, back-end, APIs, and databases.

Working within an AI-native development workflow, leveraging tools to accelerate development and reduce repetitive work.

Integrating with real-world data sources, including APIs, ETL pipelines, and third-party platforms.

Supporting ongoing tech modernisation, including tools, infrastructure, and development practices.

Collaborating closely with product, design, and stakeholders to deliver practical, high-impact solutions.



About You:
2–5 years’ experience in software development, with exposure across the full stack.

Comfortable working with technologies such as JavaScript/TypeScript, React, Python, C#, Node.js, and SQL/NoSQL databases.

Strong AI fluency, actively using AI tools in your development workflow (beyond basic prompting).

Ability to context-switch across multiple products or codebases without losing momentum.

A bias toward action, with experience working in short delivery cycles and iterating quickly.

Self-directed, proactive, and comfortable working in a fast-paced, evolving environment.

Strong communication skills and ability to work directly with stakeholders.

Nice to have:

Experience with cloud platforms (AWS/Azure), Docker, or CI/CD pipelines.

Exposure to search/analytics tools or third-party integrations.

Interest in industries such as retail, FMCG, or liquor.
"""


def main() -> None:
    posting = JobPosting(
        title="Software Engineer (AI)",
        company="The Caudex Group",
        source_url="https://au.seek.com/job/93285002?ref=applied",
        raw_text=JOB_TEXT.strip(),
    )

    extractor = OpenAIJobExtractor()
    service = JobAnalysisService(extractor)

    print("Running live OpenAI extraction...")

    analysis = service.analyse(posting)

    print("\nExtraction succeeded.\n")
    print(json.dumps(analysis.model_dump(mode="json"), indent=2))

    print("\nSmoke-test checks:")
    print(f"- Original posting bound by service: {analysis.posting is posting}")
    print(f"- Role family: {analysis.role_family.family}")
    print(f"- Seniority: {analysis.seniority.level}")
    print(f"- Technologies extracted: {len(analysis.technologies)}")
    print(f"- Responsibilities extracted: {len(analysis.responsibilities)}")
    print(f"- Compensation clarity: {analysis.compensation.clarity}")

    dumped = analysis.model_dump(mode="json")
    print(f"- Candidate-fit field absent: {'technical_fit' not in dumped}")


if __name__ == "__main__":
    main()