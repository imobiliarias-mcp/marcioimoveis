"""Configuration settings for Márcio Imóveis portal HTTP interactions."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PortalConfiguration:
    """Holds endpoint configuration, headers, and operational timeouts."""

    base_url: str = "https://marcioimoveis.net.br"
    search_path: str = "/properties-search/"
    ajax_path: str = "/wp-admin/admin-ajax.php"
    user_agent: str = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    # The server strictly requires Accept-Language to prevent HTTP 406 Not Acceptable
    accept_language: str = "pt-BR,pt;q=0.9,en;q=0.8"
    timeout_seconds: float = 20.0
    page_size: int = 6

    def build_default_headers(self) -> dict[str, str]:
        """Construct standard browser headers avoiding bot blocks and 406 errors."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": self.accept_language,
        }

    def build_ajax_headers(self) -> dict[str, str]:
        """Construct headers for admin-ajax requests."""
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": self.accept_language,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
