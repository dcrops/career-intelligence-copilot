from __future__ import annotations

import truststore

truststore.inject_into_ssl()

import json

from career_intelligence.job_analysis import JobAnalysisService, JobPosting
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor


JOB_TEXT = """
AI Engineer

Greater Melbourne Are

150K AUD/yr - 180K AUD/yr
On-site
Full-time

About the job
AI Engineer

Melbourne based, must have full working rights in Australia



About the Role

Our client is building out its internal AI capability and needs an AI Engineer to turn redesigned workflows into production grade solutions. This is not a role where you use AI tools to help you code faster. This is a role where you build the AI systems the rest of the business relies on every day.



What You'll Do

You'll take redesigned business workflows and turn them into AI systems that actually run in production, end to end. That spans everything from the underlying models and orchestration through to the infrastructure they run on and the systems they connect to. You'll also work directly with the business people who use what you build, so it needs to actually land, not just work in a demo.



What You'll Bring

This is a hands on role for someone who has genuinely built and shipped AI powered systems, not someone who has used AI tools to help them ship other things faster. You'll have several years in software, data, or automation work, a solid technical foundation, and a track record you can speak to in detail rather than describe in generalities.



*************Important: How to Apply*************

This role is genuinely about building AI systems, not using AI assisted coding tools to ship other things faster. If most of your experience is using existing AI products rather than designing and deploying your own, this likely isn't the right fit.



To apply, email your resume to kieran@discoveredpeople.com.au along with a short note (no more than 300 words) describing something you built, the problem it solved, and one thing you'd do differently in hindsight.



We're looking for evidence of things you've actually built, not tools you've operated. Applications without this note will not be considered.



MUST HAVE CURRENT, FULL WORKING RIGHTS IN AUSTRALIA
"""


def main() -> None:
    posting = JobPosting(
        title="AI Engineer",
        company="Discovered People",
        source_url="https://www.linkedin.com/jobs/search-results/?currentJobId=4438611311&eBP=CwEAAAGfgzwwv3SDTDul-PDUYtezBmV1fNWeZfNod-jgpsml0CFS29P4rZyLfBGNjEWGfI16RkozmQZMXxIiuSZxrFaQNekPrhnSl3nbFhsdROAMAab81RPE6HNXrpLnCskwie4st9mIzK2OkjOmPyU9hKuCtPdoBoixLi0hsZfvglajxGCL9uy6HVhqKedLx3TDAvZFlfe4SIMKfxoU7IwodqivdZQfEeRFeSIGGegaCpWmLgb4IWhFSY-h23EIfLhbopbJaY-c24j8vw_j3WxVuZPsgGz5qfpNJbTdTJ86H_mvvcHQzkKvFntKV5TsebU0aAmga5U7jpE705k4wHPWba2gwvqr0pKZKWUwILStaESSZDvINI9DZJpfJ8-4THDcvyn4cQbXbKVJXe-boaNPNy8N2dd-GSqLL3zaYCCth0_W2n7VLJ1fRVGxbFga0dIvZLittd6qh_5cz5RUUlYLg-UwvOK4gTqVyx0OQ2NlXfzf3OTFibyMOw&refId=4YaaZN%2FEs3R1j8NKlp83FQ%3D%3D&trackingId=p9kh7ncJPyYjtb9egFj4xg%3D%3D&keywords=full-time%20AI%20Engineer%20or%20Machine%20Learning%20Engineer%20or%20Software%20Engineer%20or%20Data%20Engineer%2C%20on-site%20or%20hybrid&origin=PREFERENCES_LANDING&originToLandingJobPostings=4435396315%2C4431071679%2C4380084305&geoId=90009521",
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