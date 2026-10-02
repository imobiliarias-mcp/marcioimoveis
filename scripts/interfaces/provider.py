"""Protocol abstraction for rental search provider implementations."""

from typing import Protocol

from scripts.domain.criteria import RentalFilter
from scripts.domain.entities import FacetCatalog, PropertyDetail, SearchPageResult
from scripts.domain.value_objects import PropertyCode


class RentalProviderProtocol(Protocol):
    """Contract for real estate rental research providers."""

    def search_rentals(self, criteria: RentalFilter) -> SearchPageResult:
        """Search rental listings using specified criteria and pagination."""
        ...

    def get_property_detail(self, property_code: PropertyCode) -> PropertyDetail:
        """Retrieve complete property detail by reference code."""
        ...

    def get_facets(self) -> FacetCatalog:
        """Retrieve available search facets and taxonomy options."""
        ...

    def search_map_rentals(self, criteria: RentalFilter) -> list[dict]:
        """Query property coordinates and summary records for map display."""
        ...
