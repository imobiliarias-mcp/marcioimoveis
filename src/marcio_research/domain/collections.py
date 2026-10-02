"""First-class collections encapsulating domain entity aggregates."""

from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marcio_research.domain.entities import FacetOption, RentalListing


class ListingCollection:
    """First-class collection of rental listings."""

    def __init__(self, items: list["RentalListing"] | None = None) -> None:
        """Initialize collection with listing items."""
        self._items = list(items) if items is not None else []

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator["RentalListing"]:
        return iter(self._items)

    def __getitem__(self, index: int) -> "RentalListing":
        return self._items[index]

    def is_empty(self) -> bool:
        """Return True when collection has no elements."""
        return len(self._items) == 0

    def to_list(self) -> list[dict]:
        """Serialize collection elements to list of dictionaries."""
        return [item.to_dictionary() for item in self._items]


class PhotoCollection:
    """First-class collection of property photo URLs."""

    def __init__(self, urls: list[str] | None = None) -> None:
        """Initialize collection with URL strings."""
        self._urls = list(urls) if urls is not None else []

    def __len__(self) -> int:
        return len(self._urls)

    def __iter__(self) -> Iterator[str]:
        return iter(self._urls)

    def __getitem__(self, index: int) -> str:
        return self._urls[index]

    def is_empty(self) -> bool:
        """Return True if no photos exist."""
        return len(self._urls) == 0

    def to_list(self) -> list[str]:
        """Return raw list of photo URLs."""
        return list(self._urls)


class FacetOptionCollection:
    """First-class collection of facet options."""

    def __init__(self, items: list["FacetOption"] | None = None) -> None:
        """Initialize collection with facet options."""
        self._items = list(items) if items is not None else []

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator["FacetOption"]:
        return iter(self._items)

    def to_list(self) -> list[dict]:
        """Serialize collection elements to list of dictionaries."""
        return [item.to_dictionary() for item in self._items]
