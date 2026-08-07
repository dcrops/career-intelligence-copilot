"""Injectable HTTP fetch boundary for FR-018 URL acquisition (M2/M3).

CI uses ``FakeHttpClient`` / fixture bytes. Live uses ``UrllibHttpClient``.
No Playwright, no session theft, no CAPTCHA bypass.

M3: prefer OS trust store via ``truststore.SSLContext`` when available so conda /
``SSL_CERT_FILE`` CA bundles that fail OpenSSL 3 path checks do not block lawful
owner fetches. This is an environment TLS fix — not scrape escalation.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HttpFetchError(Exception):
    """Fail-closed HTTP / transport failure."""

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class HttpFetchResponse:
    """Minimal successful HTTP response for acquisition."""

    url: str
    status_code: int
    body: bytes
    content_type: str | None = None


@runtime_checkable
class HttpFetchClient(Protocol):
    """Narrow fetch interface — one GET, no crawling."""

    def get(self, url: str, *, timeout_seconds: float = 20.0) -> HttpFetchResponse:
        """GET ``url`` and return body bytes, or raise ``HttpFetchError``."""
        ...


def build_default_ssl_context() -> ssl.SSLContext:
    """Build a TLS client context suitable for owner machine HTTPS.

    Prefer ``truststore`` (OS certificate store). Fall back to the stdlib default
    context when truststore is unavailable. Never disables verification.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


@dataclass(frozen=True)
class UrllibHttpClient:
    """Stdlib HTTP GET client (live owner validation / production discover)."""

    user_agent: str = (
        "CareerIntelligenceCopilot/0.1 (+local owner job acquisition; not a crawler)"
    )
    ssl_context: ssl.SSLContext | None = field(default=None, repr=False)
    """Optional injected SSL context (tests). ``None`` → ``build_default_ssl_context``."""

    def get(self, url: str, *, timeout_seconds: float = 20.0) -> HttpFetchResponse:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            },
            method="GET",
        )
        context = self.ssl_context if self.ssl_context is not None else build_default_ssl_context()
        try:
            with urlopen(  # noqa: S310
                request,
                timeout=timeout_seconds,
                context=context,
            ) as response:
                body = response.read()
                status = int(getattr(response, "status", 200) or 200)
                content_type = response.headers.get("Content-Type")
                final_url = response.geturl() or url
        except HTTPError as exc:
            raise HttpFetchError(
                f"HTTP {exc.code} fetching URL",
                kind="http_error",
                status_code=int(exc.code),
                detail=str(exc.reason),
            ) from exc
        except TimeoutError as exc:
            raise HttpFetchError(
                "Timed out fetching URL",
                kind="timeout",
                detail=str(exc),
            ) from exc
        except URLError as exc:
            reason = str(exc.reason)
            kind = "timeout" if "timed out" in reason.lower() else "network_failure"
            raise HttpFetchError(
                "Network failure fetching URL",
                kind=kind,
                detail=reason,
            ) from exc
        except OSError as exc:
            raise HttpFetchError(
                "OS error fetching URL",
                kind="network_failure",
                detail=str(exc),
            ) from exc

        if status >= 400:
            raise HttpFetchError(
                f"HTTP {status} fetching URL",
                kind="http_error",
                status_code=status,
            )
        return HttpFetchResponse(
            url=final_url,
            status_code=status,
            body=body,
            content_type=content_type,
        )


@dataclass
class FakeHttpClient:
    """Deterministic offline fetch map for tests."""

    responses: dict[str, HttpFetchResponse | HttpFetchError]
    """Map request URL → response or error instance to raise."""

    calls: list[str] | None = None

    def get(self, url: str, *, timeout_seconds: float = 20.0) -> HttpFetchResponse:
        del timeout_seconds
        if self.calls is not None:
            self.calls.append(url)
        entry = self.responses.get(url)
        if entry is None:
            raise HttpFetchError(
                "No fake response configured for URL",
                kind="network_failure",
                detail=url,
            )
        if isinstance(entry, HttpFetchError):
            raise entry
        return entry
