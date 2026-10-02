"""Resilient HTTP transport layer using standard library with error handling."""

import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from scripts.client.configuration import PortalConfiguration
from scripts.domain.exceptions import HttpTransportError


@dataclass(frozen=True)
class HttpResponse:
    """Represents raw HTTP response payload and metadata."""

    status_code: int
    body: str
    url: str


class HttpTransportProtocol(Protocol):
    """Abstract interface for HTTP transport."""

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        """Perform HTTP GET request."""
        ...

    def post(
        self,
        url: str,
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Perform HTTP POST request."""
        ...


class UrllibTransport:
    """Standard-library HTTP transport implementation."""

    def __init__(self, configuration: PortalConfiguration) -> None:
        """Initialize transport with portal configuration."""
        self._config = configuration
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create permissive SSL context for legacy certificates."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _prepare_headers(self, custom_headers: dict[str, str] | None) -> dict[str, str]:
        """Merge base headers with request-specific custom headers."""
        hdrs = self._config.build_default_headers()
        if custom_headers:
            hdrs.update(custom_headers)
        return hdrs

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        """Execute GET request returning response body."""
        all_headers = self._prepare_headers(headers)
        req = urllib.request.Request(url, headers=all_headers)
        try:
            with urllib.request.urlopen(
                req, context=self._ssl_context, timeout=self._config.timeout_seconds
            ) as resp:
                raw_bytes = resp.read()
                content = raw_bytes.decode("utf-8", errors="replace")
                return HttpResponse(status_code=resp.status, body=content, url=resp.geturl())
        except urllib.error.HTTPError as exc:
            msg = f"HTTP {exc.code} fetching {url}: {exc.reason}"
            raise HttpTransportError(msg) from exc
        except Exception as exc:
            msg = f"Network failure connecting to {url}: {exc}"
            raise HttpTransportError(msg) from exc

    def post(
        self,
        url: str,
        data: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:
        """Execute POST request with encoded form data."""
        base_headers = self._config.build_ajax_headers()
        if headers:
            base_headers.update(headers)
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded_data, headers=base_headers)
        try:
            with urllib.request.urlopen(
                req, context=self._ssl_context, timeout=self._config.timeout_seconds
            ) as resp:
                raw_bytes = resp.read()
                content = raw_bytes.decode("utf-8", errors="replace")
                return HttpResponse(status_code=resp.status, body=content, url=resp.geturl())
        except urllib.error.HTTPError as exc:
            msg = f"HTTP {exc.code} posting to {url}: {exc.reason}"
            raise HttpTransportError(msg) from exc
        except Exception as exc:
            msg = f"Network failure posting to {url}: {exc}"
            raise HttpTransportError(msg) from exc
