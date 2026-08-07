"""Generate FR-018 M4 .eml fixtures (run from repo root)."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "discovery"


def write_eml(
    name: str,
    *,
    frm: str,
    subject: str,
    html: str,
    text: str,
    mid: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = frm
    msg["To"] = "owner@example.com"
    msg["Subject"] = subject
    msg["Message-ID"] = mid
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    path = FIX / name
    path.write_bytes(msg.as_bytes())
    print("wrote", path)


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    write_eml(
        "seek_job_alert.eml",
        frm="SEEK Job Mail <jobmail@seek.com.au>",
        subject="Your SEEK job alert: AI Engineer",
        html="""<html><body>
  <h1>New jobs matching AI Engineer</h1>
  <p><a href="https://www.seek.com.au/job/93312273">AI Engineer</a>
     at Example AI Labs — Melbourne VIC</p>
  <p>Build production RAG systems with Python.</p>
  <p><a href="https://www.seek.com.au/job/93302836">Senior AI Engineer</a>
     at Contoso — Sydney NSW</p>
  <p>Lead agentic workflows for enterprise clients.</p>
  </body></html>""",
        text=(
            "AI Engineer https://www.seek.com.au/job/93312273\n"
            "Senior AI Engineer https://www.seek.com.au/job/93302836\n"
        ),
        mid="<seek-alert-001@seek.com.au>",
    )
    write_eml(
        "linkedin_job_alert_comm.eml",
        frm="LinkedIn Job Alerts <jobalerts-noreply@linkedin.com>",
        subject="Your job alerts for AI Engineer in Melbourne",
        html="""<html><body>
  <p><a href="https://www.linkedin.com/comm/jobs/view/4381552675/?trackingId=abc">Senior AI Engineer</a></p>
  <p><a href="https://www.linkedin.com/comm/jobs/view/4444879919/?trackingId=def">Generative AI Engineer</a></p>
  <p><a href="https://www.linkedin.com/jobs/view/4429615445">Legacy path still works</a></p>
  </body></html>""",
        text=(
            "Senior AI Engineer\n"
            "https://www.linkedin.com/comm/jobs/view/4381552675/?trackingId=abc\n"
            "Generative AI Engineer\n"
            "https://www.linkedin.com/comm/jobs/view/4444879919/?trackingId=def\n"
        ),
        mid="<linkedin-comm-alert-001@linkedin.com>",
    )
    write_eml(
        "linkedin_job_alert.eml",
        frm="LinkedIn Job Alerts <jobs-listings@linkedin.com>",
        subject="Your job alert for AI Engineer",
        html="""<html><body>
  <p><a href="https://www.linkedin.com/jobs/view/4429615445">Senior AI Engineer</a>
     — Fyndr Group — Melbourne</p>
  <p>Build production AI systems.</p>
  </body></html>""",
        text="Senior AI Engineer https://www.linkedin.com/jobs/view/4429615445\n",
        mid="<linkedin-alert-001@linkedin.com>",
    )
    write_eml(
        "indeed_job_alert.eml",
        frm="Indeed <alert@indeed.com>",
        subject="AI Engineer jobs in Melbourne",
        html="""<html><body>
  <p><a href="https://au.indeed.com/viewjob?jk=6449f2b22e094d45">Staff Applied AI Scientist</a></p>
  <p>Culture Amp — Melbourne VIC</p>
  </body></html>""",
        text="Staff Applied AI Scientist https://au.indeed.com/viewjob?jk=6449f2b22e094d45\n",
        mid="<indeed-alert-001@indeed.com>",
    )
    write_eml(
        "unsupported_newsletter.eml",
        frm="News <news@random-corp.example>",
        subject="Weekly tech newsletter",
        html="<html><body><p>No jobs here</p></body></html>",
        text="No jobs here",
        mid="<news-001@random-corp.example>",
    )
    write_eml(
        "malformed_seek_no_jobs.eml",
        frm="SEEK Job Mail <jobmail@seek.com.au>",
        subject="Your SEEK job alert",
        html=(
            '<html><body><p>No matching jobs today. '
            '<a href="https://www.seek.com.au/">Visit SEEK</a></p></body></html>'
        ),
        text="No matching jobs today.",
        mid="<seek-empty-001@seek.com.au>",
    )


if __name__ == "__main__":
    main()
