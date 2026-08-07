"""Narrow HTML → job text extraction for FR-018 M2/M3 (no LLM, no analysis)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from .errors import DiscoveryError


class _HtmlTextExtractor(HTMLParser):
    """Collect visible text; skip script/style/noscript."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._chunks: list[str] = []
        self._title: str | None = None
        self._in_title = False
        self._og_title: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if lowered == "title":
            self._in_title = True
        if lowered == "meta":
            attr_map = {k.lower(): (v or "") for k, v in attrs}
            if attr_map.get("property", "").lower() == "og:title":
                self._og_title = attr_map.get("content") or None

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title and self._title is None:
            self._title = text
        self._chunks.append(text)


_BLOCKED_MARKERS = (
    "captcha",
    "enable javascript",
    "please sign in",
    "sign in to continue",
    "unusual traffic",
    "access denied",
    "verify you are a human",
)

_MIN_BODY_CHARS = 80

# Live LinkedIn often 200-redirects expired jobs to search/list pages.
_LISTING_TITLE = re.compile(r"\d[\d,]+\+?\s+\S+\s+jobs?\b", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedPostingContent:
    raw_text: str
    title: str | None
    company: str | None
    warnings: tuple[str, ...]


def extract_job_content_from_html(
    html: str,
    *,
    platform: str,
    final_url: str | None = None,
) -> ExtractedPostingContent:
    """Extract posting text from HTML; fail closed on empty / blocked pages."""
    if not html or not html.strip():
        raise DiscoveryError(
            "Empty HTML body",
            detail="malformed_content",
        )

    assert_not_non_job_landing(html, platform=platform, final_url=final_url)

    lowered = html.lower()
    for marker in _BLOCKED_MARKERS:
        if marker in lowered and len(re.sub(r"\s+", "", html)) < 2000:
            # Short pages with block markers → anti-bot / login wall
            raise DiscoveryError(
                "Page appears blocked or login-walled; refusing acquisition",
                detail="blocked_response",
            )

    # Prefer platform-ish description regions when present.
    region = _extract_region(html, platform) or html
    body_parser = _HtmlTextExtractor()
    meta_parser = _HtmlTextExtractor()
    try:
        body_parser.feed(region)
        body_parser.close()
        meta_parser.feed(html)
        meta_parser.close()
    except Exception as exc:  # noqa: BLE001 — fail closed on parser errors
        raise DiscoveryError(
            "Failed to parse HTML for job content",
            detail=str(exc),
        ) from exc

    text = _normalise_whitespace("\n".join(body_parser._chunks))
    if len(text) < _MIN_BODY_CHARS:
        raise DiscoveryError(
            "Insufficient job advertisement text extracted from HTML",
            detail="malformed_content",
        )

    title = meta_parser._og_title or meta_parser._title or body_parser._og_title
    if title:
        title = _clean_title(title, platform=platform)

    if platform == "linkedin" and title and _LISTING_TITLE.search(title):
        raise DiscoveryError(
            "LinkedIn response looks like a job search listing, not a single job ad",
            detail="blocked_response",
        )

    company = _guess_company(text, platform, html=html)
    warnings: list[str] = []
    if company is None:
        warnings.append("company could not be extracted from HTML; left unset")
    if title is None:
        warnings.append("title could not be extracted from HTML; left unset")

    return ExtractedPostingContent(
        raw_text=text,
        title=title,
        company=company,
        warnings=tuple(warnings),
    )


def assert_not_non_job_landing(
    html: str,
    *,
    platform: str,
    final_url: str | None,
) -> None:
    """Fail closed when the response is clearly not a single job advertisement."""
    final = (final_url or "").lower()
    if platform == "linkedin":
        if "expired_jd_redirect" in final or "trk=expired" in final:
            raise DiscoveryError(
                "LinkedIn redirected away from the job view (expired or unavailable)",
                detail="blocked_response",
            )
        parsed = urlparse(final_url or "")
        path = (parsed.path or "").lower()
        query = parse_qs(parsed.query)
        has_view_id = bool(re.search(r"/jobs/view/\d+", path))
        has_current = bool(query.get("currentJobId") or query.get("currentjobid"))
        if final and "linkedin.com" in (parsed.hostname or "").lower():
            if "/jobs/view/" not in path and not has_current and "/jobs/" in path:
                raise DiscoveryError(
                    "LinkedIn final URL is a jobs listing, not a job view",
                    detail="blocked_response",
                )
            if has_view_id is False and has_current is False and path.rstrip("/") == "/jobs":
                raise DiscoveryError(
                    "LinkedIn final URL is the jobs hub, not a job view",
                    detail="blocked_response",
                )
    if platform == "indeed":
        lowered = html[:12000].lower()
        if "cf-mitigated" in lowered or "just a moment" in lowered:
            raise DiscoveryError(
                "Indeed response appears to be a bot-challenge interstitial",
                detail="blocked_response",
            )


def _extract_region(html: str, platform: str) -> str | None:
    patterns: list[str]
    if platform == "seek":
        patterns = [
            r'(?is)<div[^>]+data-automation=["\']jobAdDetails["\'][^>]*>(.*?)</div>',
            r'(?is)<div[^>]+data-automation=["\']jobAdDetails["\'][^>]*>.*?</section>',
            r'(?is)<div[^>]+data-automation=["\']job-detail["\'][^>]*>(.*?)</div>',
        ]
    elif platform == "linkedin":
        patterns = [
            r'(?is)<div[^>]+class=["\'][^"\']*show-more-less-html__markup[^"\']*["\'][^>]*>(.*?)</div>',
            r'(?is)<div[^>]+class=["\'][^"\']*description__text[^"\']*["\'][^>]*>(.*?)</div>',
        ]
    elif platform == "indeed":
        patterns = [
            r'(?is)<div[^>]+id=["\']jobDescriptionText["\'][^>]*>(.*?)</div>',
            r'(?is)<div[^>]+class=["\'][^"\']*jobsearch-jobDescriptionText[^"\']*["\'][^>]*>(.*?)</div>',
        ]
    else:
        patterns = []
    for pattern in patterns:
        match = re.search(pattern, html)
        if match and len(match.group(0)) > 40:
            return match.group(0)
    return None


def _normalise_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _clean_title(title: str, *, platform: str) -> str:
    cleaned = title.strip()
    if platform == "seek":
        cleaned = re.sub(
            r"\s+Job in\s+.+$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*-\s*SEEK\s*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\|\s*SEEK.*$", "", cleaned, flags=re.IGNORECASE)
    else:
        cleaned = re.sub(r"\s*\|\s*SEEK.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\|\s*LinkedIn.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*-\s*Indeed\.com.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\|\s*Indeed.*$", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip() or title.strip()


def _guess_company(text: str, platform: str, *, html: str) -> str | None:
    match = re.search(r"(?im)^company:\s*(.+)$", text)
    if match:
        return match.group(1).strip()[:120] or None
    if platform == "seek":
        advertiser = re.search(
            r'(?is)data-automation=["\']advertiser-name["\'][^>]*>([^<]+)<',
            html,
        )
        if advertiser:
            name = advertiser.group(1).strip()[:120]
            if name and "seek" not in name.lower():
                return name
        # Avoid og:site_name — usually the board brand ("SEEK Australia"), not employer.
