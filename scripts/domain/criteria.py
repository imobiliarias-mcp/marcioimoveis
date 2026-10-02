"""Rental search filter criteria and immutable builder."""

from dataclasses import dataclass, field

from scripts.domain.exceptions import InvalidFilterError
from scripts.domain.value_objects import (
    ListingPrice,
    LocationSlug,
    PropertyCode,
    RoomCount,
)


@dataclass(frozen=True)
class RentalFilter:
    """Immutable search criteria specification for rental queries."""

    locations: tuple[LocationSlug, ...] = field(default_factory=tuple)
    status: str = "alugar"
    property_types: tuple[str, ...] = field(default_factory=tuple)
    bedrooms: RoomCount | None = None
    bathrooms: RoomCount | None = None
    min_price: ListingPrice | None = None
    max_price: ListingPrice | None = None
    sort: str = "default"
    page: int = 1
    property_id: PropertyCode | None = None
    keyword: str = ""

    def __post_init__(self) -> None:
        """Validate criteria constraints."""
        if self.page < 1:
            raise InvalidFilterError("Page number must be >= 1.")

    def with_location(self, slug: str) -> "RentalFilter":
        """Return new filter adding a single location slug."""
        vo = LocationSlug(slug)
        new_locs = self.locations + (vo,)
        return self._clone(locations=new_locs)

    def with_locations(self, slugs: list[str]) -> "RentalFilter":
        """Return new filter with a batch of location slugs."""
        vos = tuple(LocationSlug(s) for s in slugs)
        return self._clone(locations=vos)

    def with_status(self, status: str) -> "RentalFilter":
        """Return new filter with updated transaction status."""
        return self._clone(status=status.strip().lower())

    def with_property_type(self, property_type: str) -> "RentalFilter":
        """Return new filter adding a property type."""
        cleaned = property_type.strip().lower()
        new_types = self.property_types + (cleaned,)
        return self._clone(property_types=new_types)

    def with_bedrooms(self, count: int) -> "RentalFilter":
        """Return new filter with bedroom count."""
        return self._clone(bedrooms=RoomCount(count))

    def with_bathrooms(self, count: int) -> "RentalFilter":
        """Return new filter with bathroom count."""
        return self._clone(bathrooms=RoomCount(count))

    def with_price_ceiling(self, price: ListingPrice) -> "RentalFilter":
        """Return new filter with maximum price ceiling."""
        return self._clone(max_price=price)

    def with_price_floor(self, price: ListingPrice) -> "RentalFilter":
        """Return new filter with minimum price floor."""
        return self._clone(min_price=price)

    def with_sort(self, sort: str) -> "RentalFilter":
        """Return new filter with sorting mode."""
        return self._clone(sort=sort.strip())

    def with_page(self, page: int) -> "RentalFilter":
        """Return new filter with updated page number."""
        return self._clone(page=page)

    def with_property_id(self, code: str) -> "RentalFilter":
        """Return new filter targeting specific property reference."""
        return self._clone(property_id=PropertyCode(code))

    def _clone(self, **changes) -> "RentalFilter":
        """Create new instance with modified fields."""
        fields = {
            "locations": self.locations,
            "status": self.status,
            "property_types": self.property_types,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "sort": self.sort,
            "page": self.page,
            "property_id": self.property_id,
            "keyword": self.keyword,
        }
        fields.update(changes)
        return RentalFilter(**fields)
