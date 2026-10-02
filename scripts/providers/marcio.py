"""Concrete rental search provider for Márcio Imóveis."""

import json

from scripts.client.configuration import PortalConfiguration
from scripts.client.http_transport import HttpTransportProtocol, UrllibTransport
from scripts.client.parsers import FacetParser, PropertyDetailParser, SearchPageParser
from scripts.client.query_builder import SearchQueryBuilder
from scripts.domain.criteria import RentalFilter
from scripts.domain.entities import FacetCatalog, PropertyDetail, SearchPageResult
from scripts.domain.value_objects import PropertyCode
from scripts.interfaces.provider import RentalProviderProtocol


class MarcioRentalProvider(RentalProviderProtocol):
    """Integrates transport, query builder, and parsers into domain operations."""

    def __init__(
        self,
        configuration: PortalConfiguration,
        transport: HttpTransportProtocol,
        query_builder: SearchQueryBuilder,
        search_parser: SearchPageParser,
        detail_parser: PropertyDetailParser,
        facet_parser: FacetParser,
    ) -> None:
        """Inject collaborating dependencies."""
        self._config = configuration
        self._transport = transport
        self._query_builder = query_builder
        self._search_parser = search_parser
        self._detail_parser = detail_parser
        self._facet_parser = facet_parser

    @classmethod
    def create_default(cls) -> "MarcioRentalProvider":
        """Factory constructor with production defaults."""
        config = PortalConfiguration()
        transport = UrllibTransport(config)
        query_builder = SearchQueryBuilder(config)
        search_parser = SearchPageParser()
        detail_parser = PropertyDetailParser()
        facet_parser = FacetParser()
        return cls(config, transport, query_builder, search_parser, detail_parser, facet_parser)

    def search_rentals(self, criteria: RentalFilter) -> SearchPageResult:
        """Execute rental search against the portal."""
        url = self._query_builder.build_search_url(criteria)
        response = self._transport.get(url)
        return self._search_parser.parse(response.body)

    def get_property_detail(self, property_code: PropertyCode) -> PropertyDetail:
        """Fetch property details resolving code or direct slug."""
        code_str = str(property_code).strip()
        # If code looks like a full URL or slug
        if code_str.startswith("http"):
            target_url = code_str
        elif "/" in code_str:
            target_url = f"{self._config.base_url.rstrip('/')}/{code_str.strip('/')}/"
        else:
            # First attempt: search by property ID to locate exact listing URL
            target_url = self._resolve_property_url(code_str)

        response = self._transport.get(target_url)
        return self._detail_parser.parse(response.body, target_url)

    def _resolve_property_url(self, code_str: str) -> str:
        """Resolve property URL from property-id query."""
        search_filter = RentalFilter(status="").with_property_id(code_str)
        url = self._query_builder.build_search_url(search_filter)
        response = self._transport.get(url)
        result = self._search_parser.parse(response.body)
        if len(result.listings) > 0:
            return result.listings[0].url
        # If not found via search filter, attempt standard /imovel/{code}/ fallback
        numeric_id = PropertyCode(code_str).numeric_id()
        fallback_url = f"{self._config.base_url.rstrip('/')}/imovel/rh-{numeric_id}/"
        return fallback_url

    def get_facets(self) -> FacetCatalog:
        """Extract available locations tree, types, and statuses."""
        base_search_url = f"{self._config.base_url.rstrip('/')}{self._config.search_path}"
        response = self._transport.get(base_search_url)
        return self._facet_parser.parse(response.body)

    def search_map_rentals(self, criteria: RentalFilter) -> list[dict]:
        """Query property coordinates and summary records for map display."""
        payload = self._query_builder.build_map_ajax_payload(criteria)
        ajax_url = f"{self._config.base_url.rstrip('/')}{self._config.ajax_path}"
        response = self._transport.post(ajax_url, payload)
        data = json.loads(response.body)
        if isinstance(data, dict) and "data" in data and "propertiesData" in data["data"]:
            return data["data"]["propertiesData"]
        return []
