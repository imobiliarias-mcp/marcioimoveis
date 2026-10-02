"""Domain-specific exceptions for Márcio Imóveis rental research."""


class RentalResearchError(Exception):
    """Base exception for all portal research errors."""


class InvalidFilterError(RentalResearchError):
    """Raised when search filter criteria violate validation rules."""


class PropertyNotFoundError(RentalResearchError):
    """Raised when a requested property cannot be found or resolved."""


class HttpTransportError(RentalResearchError):
    """Raised when network transport or HTTP request fails."""


class ParserError(RentalResearchError):
    """Raised when HTML or JSON response cannot be parsed."""
