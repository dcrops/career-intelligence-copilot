"""Parse owner-supplied job-alert ``.eml`` files (FR-018 M4).

Owner saves alert emails as ``.eml`` (no IMAP/mailbox client in M4).
Fail closed on unsupported senders and digests with no extractable job URLs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

from .errors import DiscoveryUnsupportedSourceError, DiscoveryValidationError

# Allow-listed alert senders (substring match on From header, case-insensitive).
_SEEK_FROM = (
    "jobmail@seek.com.au",
    "noreply@seek.com.au",
    "jobs@seek.com.au",
    "alert@seek.com.au",
    "seek.com.au",
)
_LINKEDIN_FROM = (
    "jobs-listings@linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "linkedin.com",
)
_INDEED_FROM = (
    "alert@indeed.com",
    "noreply@indeed.com",
    "indeed.com",
)

_SEEK_JOB_HREF = re.compile(
    r"https?://(?:www\.)?(?:au\.)?seek\.com(?:\.au)?/job/(\d+)",
    re.IGNORECASE,
)
_LINKEDIN_JOB_HREF = re.compile(
    # Alert digests currently use /comm/jobs/view/<id>/; older mail uses /jobs/view/<id>.
    r"https?://(?:[a-z]+\.)?linkedin\.com/(?:comm/)?jobs/view/(\d+)",
    re.IGNORECASE,
)
_LINKEDIN_SLUG_HREF = re.compile(
    r"https?://(?:[a-z]+\.)?linkedin\.com/(?:comm/)?jobs/view/[^?\s\"'<>]*?(\d{6,})",
    re.IGNORECASE,
)
_INDEED_JOB_HREF = re.compile(
    r"https?://(?:[a-z]+\.)?indeed\.com/[^\s\"'<>]*[?&]jk=([a-f0-9]{16,32})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedEmailJob:
    """One job advertisement extracted from a job-alert email."""

    index: int
    platform: str
    job_url: str
    title: str | None
    company: str | None
    snippet: str


@dataclass(frozen=True)
class ParsedJobAlertEmail:
    """Parsed job-alert email with zero or more job entries."""

    path: Path
    message_id: str
    from_addr: str
    subject: str
    platform: str
    jobs: tuple[ParsedEmailJob, ...]


class _HrefCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._text_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = None
        for key, value in attrs:
            if key.lower() == "href" and value:
                href = value.strip()
                break
        self._current_href = href
        self._text_chunks = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = " ".join(self._text_chunks).strip()
        self.hrefs.append((self._current_href, text))
        self._current_href = None
        self._text_chunks = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            chunk = data.strip()
            if chunk:
                self._text_chunks.append(chunk)


def parse_job_alert_email(path: Path | str) -> ParsedJobAlertEmail:
    """Parse a ``.eml`` file into platform + jobs; fail closed if unsupported."""
    eml_path = Path(path)
    if not eml_path.is_file():
        raise DiscoveryValidationError(
            "Email file does not exist",
            detail=str(eml_path),
        )
    if eml_path.suffix.lower() != ".eml":
        raise DiscoveryValidationError(
            "Email acquisition requires a .eml file",
            detail=eml_path.suffix,
        )

    try:
        raw = eml_path.read_bytes()
        message = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as exc:  # noqa: BLE001
        raise DiscoveryValidationError(
            "Failed to parse email MIME",
            detail=str(exc),
        ) from exc

    from_addr = str(message.get("From", "") or "")
    subject = str(message.get("Subject", "") or "")
    message_id = _stable_message_id(message, eml_path)
    platform = classify_job_alert_sender(from_addr, subject)
    if platform is None:
        raise DiscoveryUnsupportedSourceError(
            "Email sender is not a supported job-alert source",
            detail=from_addr or "(missing From)",
        )

    html_body, text_body = _extract_bodies(message)
    jobs = _extract_jobs(
        platform=platform,
        html_body=html_body,
        text_body=text_body,
    )
    if not jobs:
        raise DiscoveryUnsupportedSourceError(
            "No supported job URLs found in job-alert email",
            detail=platform,
        )

    return ParsedJobAlertEmail(
        path=eml_path.resolve(),
        message_id=message_id,
        from_addr=from_addr,
        subject=subject,
        platform=platform,
        jobs=tuple(jobs),
    )


def classify_job_alert_sender(from_addr: str, subject: str = "") -> str | None:
    """Return seek|linkedin|indeed or None for unsupported senders."""
    blob = f"{from_addr} {subject}".lower()
    # Prefer specific platforms; avoid matching generic "com" alone.
    if any(token in blob for token in ("seek.com.au", "seek.com", "@seek.")):
        return "seek"
    if "linkedin" in blob:
        return "linkedin"
    if "indeed" in blob:
        return "indeed"
    return None


def email_locator(path: Path | str, job_index: int) -> str:
    """Build OpportunitySource.locator for one job inside an .eml digest."""
    if job_index < 0:
        raise DiscoveryValidationError("job index must be >= 0", detail=str(job_index))
    resolved = Path(path).resolve()
    return f"{resolved}#job={job_index}"


def parse_email_locator(locator: str) -> tuple[Path, int]:
    """Split ``path.eml#job=N`` into path and index."""
    if "#job=" not in locator:
        raise DiscoveryValidationError(
            "email locator requires #job=<index>",
            detail=locator,
        )
    path_part, _, fragment = locator.partition("#")
    if not fragment.startswith("job=") or not fragment[4:].isdigit():
        raise DiscoveryValidationError(
            "email locator fragment must be job=<int>",
            detail=fragment,
        )
    return Path(path_part), int(fragment[4:])


def _stable_message_id(message: Message, path: Path) -> str:
    mid = str(message.get("Message-ID", "") or "").strip()
    if mid:
        return mid.strip("<>")
    # Deterministic fallback for fixtures without Message-ID.
    return f"eml:{path.name}"


def _extract_bodies(message: Message) -> tuple[str, str]:
    html_parts: list[str] = []
    text_parts: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() == "multipart":
                continue
            ctype = (part.get_content_type() or "").lower()
            try:
                payload = part.get_content()
            except Exception:  # noqa: BLE001
                continue
            if not isinstance(payload, str):
                continue
            if ctype == "text/html":
                html_parts.append(payload)
            elif ctype == "text/plain":
                text_parts.append(payload)
    else:
        ctype = (message.get_content_type() or "").lower()
        try:
            payload = message.get_content()
        except Exception:  # noqa: BLE001
            payload = ""
        if isinstance(payload, str):
            if ctype == "text/html":
                html_parts.append(payload)
            else:
                text_parts.append(payload)

    return "\n".join(html_parts), "\n".join(text_parts)


def _extract_jobs(
    *,
    platform: str,
    html_body: str,
    text_body: str,
) -> list[ParsedEmailJob]:
    # LinkedIn digests put title/company above ``View job:`` in plaintext;
    # HTML anchors are often empty image/tracking links.
    if platform == "linkedin" and text_body:
        card_jobs = _linkedin_plaintext_cards(text_body)
        if card_jobs:
            return card_jobs

    seen: set[str] = set()
    jobs: list[ParsedEmailJob] = []

    candidates: list[tuple[str, str | None]] = []
    if html_body:
        collector = _HrefCollector()
        try:
            collector.feed(html_body)
            collector.close()
        except Exception:  # noqa: BLE001
            collector.hrefs = []
        for href, text in collector.hrefs:
            normalised = _normalise_job_url(platform, href)
            if normalised:
                candidates.append((normalised, text or None))

    # Plain-text fallback: scan for URLs.
    for match in re.finditer(r"https?://[^\s<>\"']+", text_body or ""):
        normalised = _normalise_job_url(platform, match.group(0))
        if normalised:
            candidates.append((normalised, None))

    # Also scan HTML as raw text for boards that wrap URLs oddly.
    for match in re.finditer(r"https?://[^\s<>\"']+", html_body or ""):
        normalised = _normalise_job_url(platform, match.group(0))
        if normalised:
            candidates.append((normalised, None))

    for url, anchor_text in candidates:
        if url in seen:
            continue
        seen.add(url)
        title = _clean_title(anchor_text) if anchor_text else None
        snippet = _snippet_for_job(
            platform=platform,
            job_url=url,
            title=title,
            html_body=html_body,
            text_body=text_body,
        )
        jobs.append(
            ParsedEmailJob(
                index=len(jobs),
                platform=platform,
                job_url=url,
                title=title,
                company=None,
                snippet=snippet,
            )
        )
    return jobs


_LINKEDIN_VIEW_JOB = re.compile(
    r"(?im)^\s*View job:\s*(https?://\S+)",
)
_LINKEDIN_SEP = re.compile(r"^-{5,}$")
_LINKEDIN_CONNECTIONS = re.compile(r"(?i)^\d+\s+connections?$")
_LINKEDIN_SKIP_EXACT = frozenset(
    {
        "this company is actively hiring",
        "new jobs match your preferences.",
        "new jobs match your preferences",
    }
)


def _is_linkedin_skip_line(line: str) -> bool:
    cleaned = line.strip()
    if not cleaned or _LINKEDIN_SEP.fullmatch(cleaned):
        return True
    low = cleaned.lower()
    if low in _LINKEDIN_SKIP_EXACT:
        return True
    if _LINKEDIN_CONNECTIONS.fullmatch(cleaned):
        return True
    return False


def _linkedin_plaintext_cards(text_body: str) -> list[ParsedEmailJob]:
    """Parse LinkedIn alert cards: Title / Company / Location / View job: URL."""
    jobs: list[ParsedEmailJob] = []
    seen: set[str] = set()
    for match in _LINKEDIN_VIEW_JOB.finditer(text_body):
        normalised = _normalise_job_url("linkedin", match.group(1))
        if not normalised or normalised in seen:
            continue
        lines = [
            ln.strip()
            for ln in text_body[: match.start()].splitlines()
            if ln.strip() and not _is_linkedin_skip_line(ln)
        ]
        if len(lines) < 3:
            continue
        location, company, title = lines[-1], lines[-2], lines[-3]
        if title.lower().startswith("http") or company.lower().startswith("http"):
            continue
        title_clean = _clean_title(title)
        company_clean = _clean_title(company)
        snippet = _snippet_for_job(
            platform="linkedin",
            job_url=normalised,
            title=title_clean,
            company=company_clean,
            location=_clean_title(location),
            html_body="",
            text_body=text_body,
        )
        seen.add(normalised)
        jobs.append(
            ParsedEmailJob(
                index=len(jobs),
                platform="linkedin",
                job_url=normalised,
                title=title_clean,
                company=company_clean,
                snippet=snippet,
            )
        )
    return jobs


def _normalise_job_url(platform: str, href: str) -> str | None:
    cleaned = unquote(href.strip()).split("&amp;")[0]
    # Strip common tracking wrappers that embed the real URL as a query param.
    if "seek.com" in cleaned.lower() or platform == "seek":
        match = _SEEK_JOB_HREF.search(cleaned)
        if match:
            return f"https://www.seek.com.au/job/{match.group(1)}"
    if "linkedin.com" in cleaned.lower() or platform == "linkedin":
        match = _LINKEDIN_JOB_HREF.search(cleaned) or _LINKEDIN_SLUG_HREF.search(cleaned)
        if match:
            return f"https://www.linkedin.com/jobs/view/{match.group(1)}"
    if "indeed.com" in cleaned.lower() or platform == "indeed":
        match = _INDEED_JOB_HREF.search(cleaned)
        if match:
            return f"https://www.indeed.com/viewjob?jk={match.group(1).lower()}"
    return None


def _clean_title(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) < 3:
        return None
    # Ignore pure CTA anchors.
    if cleaned.lower() in {"view job", "apply", "see job", "view", "apply now"}:
        return None
    return cleaned[:200]


def _snippet_for_job(
    *,
    platform: str,
    job_url: str,
    title: str | None,
    html_body: str,
    text_body: str,
    company: str | None = None,
    location: str | None = None,
) -> str:
    """Build enough raw text for JobPosting / analysis without live board fetch."""
    lines: list[str] = []
    if title:
        lines.append(f"Title: {title}")
    if company:
        lines.append(f"Company: {company}")
    if location:
        lines.append(f"Location: {location}")
    lines.append(f"Source: {platform} job alert")
    lines.append(f"Job URL: {job_url}")
    # Prefer a short window of plain text around the URL if present.
    # For LinkedIn, match either the canonical /jobs/view/ URL or /comm/ form.
    body = text_body or _html_to_rough_text(html_body)
    if body:
        idx = body.find(job_url)
        if idx < 0:
            job_id_match = re.search(r"/jobs/view/(\d+)", job_url)
            if job_id_match:
                needle = f"/jobs/view/{job_id_match.group(1)}"
                idx = body.find(needle)
                if idx < 0:
                    idx = body.find(f"/comm/jobs/view/{job_id_match.group(1)}")
        if idx >= 0:
            window = body[max(0, idx - 280) : idx + 120]
            lines.append(_normalise_ws(window))
        elif not (title and company):
            lines.append(_normalise_ws(body)[:800])
    text = "\n".join(line for line in lines if line)
    if len(text) < 80:
        # Pad with explicit context so JobPosting / fixture analysis can run.
        text = (
            f"{text}\n"
            f"Job advertisement acquired from a {platform} email alert.\n"
            f"Owner should review the linked posting at {job_url}."
        )
    return text


def _html_to_rough_text(html: str) -> str:
    if not html:
        return ""
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return _normalise_ws(text)


def _normalise_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", re.sub(r"\n+", "\n", text)).strip()
