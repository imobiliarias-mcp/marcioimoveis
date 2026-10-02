"""Query builder transforming domain search criteria into URL paths and parameters."""

import urllib.parse

from marcio_research.client.configuration import PortalConfiguration
from marcio_research.domain.criteria import RentalFilter


class SearchQueryBuilder:
    """Constructs canonical search URLs and parameters for Márcio Imóveis."""

    def __init__(self, configuration: PortalConfiguration) -> None:
        """Initialize query builder with portal configuration."""
        self._config = configuration

    def build_query_params(self, criteria: RentalFilter) -> list[tuple[str, str]]:
        """Assemble ordered list of key-value query parameters."""
        pairs: list[tuple[str, str]] = []
        for loc in criteria.locations:
            pairs.append(("location[]", str(loc)))
        for ptype in criteria.property_types:
            pairs.append(("type[]", ptype))
        if criteria.status:
            pairs.append(("status", criteria.status))
        if criteria.bedrooms:
            pairs.append(("bedrooms", str(criteria.bedrooms)))
        if criteria.bathrooms:
            pairs.append(("bathrooms", str(criteria.bathrooms)))
        if criteria.min_price:
            pairs.append(("min-price", str(criteria.min_price.to_integer())))
        if criteria.max_price:
            pairs.append(("max-price", str(criteria.max_price.to_integer())))
        if criteria.sort and criteria.sort != "default":
            pairs.append(("sort-properties", criteria.sort))
        if criteria.property_id:
            pairs.append(("property-id", str(criteria.property_id)))
        if criteria.keyword:
            pairs.append(("keyword", criteria.keyword))
        return pairs

    def build_search_url(self, criteria: RentalFilter) -> str:
        """Construct full search URL with pagination segment and query string."""
        base = self._config.base_url.rstrip("/")
        path_prefix = self._config.search_path.strip("/")
        if criteria.page > 1:
            full_path = f"/{path_prefix}/page/{criteria.page}/"
        else:
            full_path = f"/{path_prefix}/"

        params = self.build_query_params(criteria)
        if not params:
            return f"{base}{full_path}"

        query_string = urllib.parse.urlencode(params)
        return f"{base}{full_path}?{query_string}"

    def build_map_ajax_payload(self, criteria: RentalFilter) -> dict[str, str]:
        """Construct POST payload for realhomes_map_ajax_search_results."""
        payload: dict[str, str] = {
            "action": "realhomes_map_ajax_search_results",
        }
        if criteria.status:
            payload["statuses"] = criteria.status
        if criteria.bedrooms:
            payload["bedrooms"] = str(criteria.bedrooms)
        if criteria.bathrooms:
            payload["bathrooms"] = str(criteria.bathrooms)
        if criteria.min_price:
            payload["minPrice"] = str(criteria.min_price.to_integer())
        if criteria.max_price:
            payload["maxPrice"] = str(criteria.max_price.to_integer())
        if criteria.page > 1:
            payload["page"] = str(criteria.page)
        return payload
