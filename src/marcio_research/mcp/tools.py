"""Model Context Protocol (MCP) tool adapters for Central Rental Research."""

from marcio_research.domain.criteria import RentalFilter
from marcio_research.domain.value_objects import ListingPrice, PropertyCode
from marcio_research.interfaces.provider import RentalProviderProtocol
from marcio_research.providers.marcio import MarcioRentalProvider


class MarcioMcpAdapter:
    """Adapts domain rental provider for consumption by MCP servers and tool registries."""

    def __init__(self, provider: RentalProviderProtocol) -> None:
        """Initialize adapter with an abstract rental provider."""
        self._provider = provider

    @classmethod
    def create_default(cls) -> "MarcioMcpAdapter":
        """Factory constructor instantiating the default Márcio Imóveis provider."""
        default_provider = MarcioRentalProvider.create_default()
        return cls(provider=default_provider)

    def _apply_constraints(
        self,
        target_filter: RentalFilter,
        min_price: float,
        max_price: float,
        bedrooms: int,
        bathrooms: int,
        property_type: str,
        sort: str,
    ) -> RentalFilter:
        """Apply numerical and categorical constraints to search filter."""
        working = target_filter
        if bedrooms > 0:
            working = working.with_bedrooms(bedrooms)
        if bathrooms > 0:
            working = working.with_bathrooms(bathrooms)
        if min_price > 0.0:
            working = working.with_price_floor(ListingPrice(min_price))
        if max_price > 0.0:
            working = working.with_price_ceiling(ListingPrice(max_price))
        if property_type:
            working = working.with_property_type(property_type)
        if sort and sort != "default":
            working = working.with_sort(sort)
        return working

    def _assemble_filter(
        self,
        locations: list[str] | None,
        min_price: float,
        max_price: float,
        bedrooms: int,
        bathrooms: int,
        property_type: str,
        sort: str,
        page: int,
    ) -> RentalFilter:
        """Construct a validated RentalFilter from tool arguments."""
        working = RentalFilter().with_page(page)
        if locations:
            working = working.with_locations(locations)
        return self._apply_constraints(
            working, min_price, max_price, bedrooms, bathrooms, property_type, sort
        )

    def search_rentals(
        self,
        locations: list[str] | None = None,
        min_price: float = 0.0,
        max_price: float = 0.0,
        bedrooms: int = 0,
        bathrooms: int = 0,
        property_type: str = "",
        sort: str = "default",
        page: int = 1,
    ) -> dict:
        """Execute a rental property search for an MCP tool call."""
        search_filter = self._assemble_filter(
            locations, min_price, max_price, bedrooms, bathrooms, property_type, sort, page
        )
        search_result = self._provider.search_rentals(search_filter)
        return search_result.to_dictionary()

    def get_property_detail(self, property_code: str) -> dict:
        """Retrieve complete property detail for an MCP tool call."""
        code_vo = PropertyCode(property_code)
        property_detail = self._provider.get_property_detail(code_vo)
        return property_detail.to_dictionary()

    def get_facets(self) -> dict:
        """Retrieve available search facets and taxonomy options for an MCP tool call."""
        facets = self._provider.get_facets()
        return facets.to_dictionary()

    def search_map_rentals(
        self,
        bedrooms: int = 0,
        bathrooms: int = 0,
        min_price: float = 0.0,
        max_price: float = 0.0,
    ) -> list[dict]:
        """Query geo-located rental properties for map visualization."""
        base_filter = RentalFilter(status="alugar")
        criteria = self._apply_constraints(
            base_filter, min_price, max_price, bedrooms, bathrooms, "", "default"
        )
        return self._provider.search_map_rentals(criteria)
