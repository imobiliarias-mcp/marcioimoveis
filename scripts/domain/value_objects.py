"""Domain value objects enforcing validation and encapsulation."""

import re
from dataclasses import dataclass

from scripts.domain.exceptions import InvalidFilterError


@dataclass(frozen=True)
class PropertyCode:
    """Encapsulates and validates property reference codes."""

    value: str

    def __post_init__(self) -> None:
        """Validate non-empty code value."""
        cleaned = self.value.strip()
        if not cleaned:
            raise InvalidFilterError("PropertyCode cannot be empty.")
        object.__setattr__(self, "value", cleaned)

    def numeric_id(self) -> str:
        """Extract numeric digits from the code value."""
        digits = re.findall(r"\d+", self.value)
        if not digits:
            return self.value
        return "".join(digits)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ListingPrice:
    """Encapsulates monetary price in Brazilian Reais (BRL)."""

    amount: float

    def __post_init__(self) -> None:
        """Validate non-negative price amount."""
        if self.amount < 0.0:
            raise InvalidFilterError("ListingPrice cannot be negative.")

    def format_brl(self) -> str:
        """Format price as Brazilian currency string."""
        formatted = f"{self.amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

    def to_integer(self) -> int:
        """Return rounded integer representation."""
        return round(self.amount)

    def __str__(self) -> str:
        return self.format_brl()


@dataclass(frozen=True)
class LocationSlug:
    """Encapsulates normalized location slug."""

    value: str

    def __post_init__(self) -> None:
        """Validate slug string."""
        cleaned = self.value.strip().lower()
        if not cleaned:
            raise InvalidFilterError("LocationSlug cannot be empty.")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RoomCount:
    """Encapsulates room or amenity count."""

    count: int

    def __post_init__(self) -> None:
        """Validate non-negative room count."""
        if self.count < 0:
            raise InvalidFilterError("RoomCount cannot be negative.")

    def __int__(self) -> int:
        return self.count

    def __str__(self) -> str:
        return str(self.count)
