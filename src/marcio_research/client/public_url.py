"""Public property URL resolution at the search parser boundary."""

from urllib.parse import urlencode, urljoin, urlsplit

from marcio_research.domain.exceptions import ParserError
from marcio_research.domain.value_objects import PropertyCode


class PublicPropertyUrlResolver:
    """Resolve listing href values without using the Glue/API listing ID."""

    def __init__(self, public_base_url: str) -> None:
        """Initialize with the configured public website origin."""
        parsed_base = urlsplit(public_base_url.strip())
        if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
            raise ValueError(f"Invalid public base URL: {public_base_url}")
        self._public_base_url = f"{parsed_base.scheme}://{parsed_base.netloc}".rstrip("/")
        self._public_host = self._normalize_host(parsed_base.hostname)

    def resolve(self, href: str, property_code: PropertyCode) -> str:
        """Return an absolute public URL or the documented post-ID lookup."""
        if not href.strip():
            return self._build_post_id_fallback(property_code)
        resolved_url = urljoin(f"{self._public_base_url}/", href.strip())
        self._validate_public_url(resolved_url, property_code)
        return resolved_url

    def _build_post_id_fallback(self, property_code: PropertyCode) -> str:
        """Use the documented WordPress lookup only for a numeric card code."""
        numeric_id = property_code.numeric_id()
        if not numeric_id.isdigit():
            raise ParserError(f"No public URL or documented ID fallback for {property_code}")
        query_string = urlencode({"post_type": "property", "p": numeric_id})
        return f"{self._public_base_url}/?{query_string}"

    def _validate_public_url(self, url: str, property_code: PropertyCode) -> None:
        """Reject foreign, non-web, and non-property public links."""
        try:
            parsed_url = urlsplit(url)
        except ValueError as error:
            raise ParserError(f"Invalid public URL for {property_code}: {url}") from error
        same_host = self._normalize_host(parsed_url.hostname) == self._public_host
        has_credentials = parsed_url.username is not None or parsed_url.password is not None
        valid_scheme = parsed_url.scheme in {"http", "https"}
        valid_detail_path = self._is_property_detail_path(parsed_url.path)
        if (
            not valid_scheme
            or not parsed_url.hostname
            or not same_host
            or has_credentials
            or not valid_detail_path
        ):
            raise ParserError(f"Invalid public URL for {property_code}: {url}")

    def _is_property_detail_path(self, path: str) -> bool:
        """Allow documented property routes and reject search or media paths."""
        normalized_path = path.lower()
        is_property_route = normalized_path.startswith(("/imovel/", "/propriedade/"))
        has_property_slug = self._has_property_slug(normalized_path)
        image_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")
        is_image = normalized_path.endswith(image_extensions)
        return is_property_route and has_property_slug and not is_image

    def _has_property_slug(self, path: str) -> bool:
        """Require a nonempty slug after either supported route prefix."""
        imovel_path = path.removeprefix("/imovel/")
        imovel_slug = imovel_path.strip("/")
        propriedade_path = path.removeprefix("/propriedade/")
        propriedade_slug = propriedade_path.strip("/")
        return bool(imovel_slug or propriedade_slug)

    def _normalize_host(self, hostname: str | None) -> str:
        """Treat www and apex names as the same configured agency host."""
        return (hostname or "").removeprefix("www.").lower()
