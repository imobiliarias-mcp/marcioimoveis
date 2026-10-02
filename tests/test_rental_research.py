"""Unit and integration test suite for Márcio Imóveis rental research modules."""

import unittest
from contextlib import redirect_stdout
from io import StringIO

from marcio_research.client.configuration import (
    PortalConfiguration as CorePortalConfiguration,
)
from marcio_research.client.http_transport import HttpResponse as CoreHttpResponse
from marcio_research.client.parsers import FacetParser as CoreFacetParser
from marcio_research.client.parsers import (
    PropertyDetailParser as CorePropertyDetailParser,
)
from marcio_research.client.parsers import SearchPageParser as CoreSearchPageParser
from marcio_research.client.query_builder import (
    SearchQueryBuilder as CoreSearchQueryBuilder,
)
from marcio_research.domain.exceptions import ParserError as CoreParserError
from marcio_research.providers.marcio import (
    MarcioRentalProvider as CoreMarcioRentalProvider,
)
from scripts import run_search
from scripts.client.configuration import PortalConfiguration
from scripts.client.http_transport import HttpResponse
from scripts.client.parsers import (
    FacetParser,
    ParserError,
    PriceTextExtractor,
    PropertyDetailParser,
    SearchPageParser,
)
from scripts.client.query_builder import SearchQueryBuilder
from scripts.domain.collections import (
    ListingCollection,
    PhotoCollection,
)
from scripts.domain.criteria import RentalFilter
from scripts.domain.entities import RentalListing
from scripts.domain.exceptions import InvalidFilterError
from scripts.domain.value_objects import (
    ListingPrice,
    LocationSlug,
    PropertyCode,
    RoomCount,
)
from scripts.mcp.tools import MarcioMcpAdapter
from scripts.providers.marcio import MarcioRentalProvider


class TestValueObjects(unittest.TestCase):
    """Test domain value objects and validation constraints."""

    def test_property_code_valid(self) -> None:
        code = PropertyCode("RH-17772")
        self.assertEqual(str(code), "RH-17772")
        self.assertEqual(code.numeric_id(), "17772")

    def test_property_code_whitespace_stripped(self) -> None:
        code = PropertyCode("  17803  ")
        self.assertEqual(str(code), "17803")
        self.assertEqual(code.numeric_id(), "17803")

    def test_property_code_empty_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            PropertyCode("")

    def test_listing_price_valid(self) -> None:
        price = ListingPrice(1200.0)
        self.assertEqual(price.amount, 1200.0)
        self.assertEqual(price.to_integer(), 1200)
        self.assertIn("1.200,00", price.format_brl())

    def test_listing_price_negative_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            ListingPrice(-1.0)

    def test_location_slug_valid(self) -> None:
        slug = LocationSlug("Timoteo")
        self.assertEqual(str(slug), "timoteo")

    def test_location_slug_empty_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            LocationSlug("  ")

    def test_room_count_valid(self) -> None:
        rc = RoomCount(3)
        self.assertEqual(int(rc), 3)

    def test_room_count_negative_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            RoomCount(-1)


class TestCriteria(unittest.TestCase):
    """Test immutable rental criteria builder."""

    def test_default_values(self) -> None:
        rf = RentalFilter()
        self.assertEqual(rf.status, "alugar")
        self.assertEqual(rf.page, 1)
        self.assertEqual(rf.sort, "default")
        self.assertEqual(len(rf.locations), 0)

    def test_immutable_updates(self) -> None:
        rf = RentalFilter()
        updated = (
            rf.with_location("timoteo")
            .with_bedrooms(2)
            .with_bathrooms(1)
            .with_price_floor(ListingPrice(500.0))
            .with_price_ceiling(ListingPrice(2000.0))
            .with_property_type("apartamento")
            .with_sort("price-asc")
            .with_page(2)
        )
        # Original remains unchanged
        self.assertEqual(len(rf.locations), 0)
        self.assertEqual(rf.page, 1)

        # Updated contains criteria
        self.assertEqual(len(updated.locations), 1)
        self.assertEqual(int(updated.bedrooms), 2)
        self.assertEqual(int(updated.bathrooms), 1)
        self.assertEqual(updated.min_price.amount, 500.0)
        self.assertEqual(updated.max_price.amount, 2000.0)
        self.assertIn("apartamento", updated.property_types)
        self.assertEqual(updated.sort, "price-asc")
        self.assertEqual(updated.page, 2)

    def test_invalid_page_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            RentalFilter().with_page(0)


class TestQueryBuilder(unittest.TestCase):
    """Test URL building and parameter serialization."""

    def setUp(self) -> None:
        self.config = PortalConfiguration()
        self.builder = SearchQueryBuilder(self.config)

    def test_page_one_url(self) -> None:
        rf = RentalFilter().with_location("timoteo").with_bedrooms(2)
        url = self.builder.build_search_url(rf)
        self.assertTrue(url.startswith("https://marcioimoveis.net.br/properties-search/?"))
        self.assertIn("location%5B%5D=timoteo", url)
        self.assertIn("bedrooms=2", url)
        self.assertIn("status=alugar", url)

    def test_pagination_path(self) -> None:
        rf = RentalFilter().with_page(3).with_status("alugar")
        url = self.builder.build_search_url(rf)
        self.assertTrue(url.startswith("https://marcioimoveis.net.br/properties-search/page/3/?"))

    def test_map_ajax_payload(self) -> None:
        rf = RentalFilter().with_bedrooms(2).with_bathrooms(1).with_price_ceiling(ListingPrice(1500.0))
        payload = self.builder.build_map_ajax_payload(rf)
        self.assertEqual(payload["action"], "realhomes_map_ajax_search_results")
        self.assertEqual(payload["bedrooms"], "2")
        self.assertEqual(payload["bathrooms"], "1")
        self.assertEqual(payload["maxPrice"], "1500")


class TestCollections(unittest.TestCase):
    """Test first-class collections."""

    def test_listing_collection(self) -> None:
        lc = ListingCollection()
        self.assertTrue(lc.is_empty())
        self.assertEqual(len(lc), 0)

        item = RentalListing(
            title="Apartamento Teste",
            property_code=PropertyCode("RH-001"),
            url="https://marcioimoveis.net.br/imovel/teste/",
            price=ListingPrice(1000.0),
        )
        lc2 = ListingCollection([item])
        self.assertFalse(lc2.is_empty())
        self.assertEqual(len(lc2), 1)
        self.assertEqual(lc2[0].title, "Apartamento Teste")
        serialized = lc2.to_list()
        self.assertEqual(len(serialized), 1)
        self.assertEqual(serialized[0]["property_code"], "RH-001")

    def test_photo_collection(self) -> None:
        pc = PhotoCollection(["https://example.com/1.jpg", "https://example.com/2.jpg"])
        self.assertEqual(len(pc), 2)
        self.assertEqual(pc[0], "https://example.com/1.jpg")
        self.assertEqual(len(pc.to_list()), 2)


class TestParsers(unittest.TestCase):
    """Test HTML and currency parsers."""

    def test_price_text_extractor(self) -> None:
        self.assertEqual(PriceTextExtractor.extract("R$1,150").amount, 1150.0)
        self.assertEqual(PriceTextExtractor.extract("R$ 2.000").amount, 2000.0)
        self.assertEqual(PriceTextExtractor.extract("R$ 1.400,00").amount, 1400.0)
        self.assertEqual(PriceTextExtractor.extract("R$350").amount, 350.0)
        self.assertIsNone(PriceTextExtractor.extract(""))

    def test_search_parser_empty_page(self) -> None:
        html = """
        <div class="rh_pagination__stats" data-page="1" data-max="1" data-total-properties="0"></div>
        <div class="rh_page__listing"><p class="rh_not_found">Nenhum Resultado Encontrado!</p></div>
        """
        parser = SearchPageParser()
        result = parser.parse(html)
        self.assertEqual(result.total_properties, 0)
        self.assertEqual(result.current_page, 1)
        self.assertEqual(len(result.listings), 0)
        self.assertFalse(result.has_next_page)


class TestPublicPropertyUrls(unittest.TestCase):
    """Verify public property URL resolution remains aligned across layers."""

    def _card_html(self, href: str | None = "/propriedade/casa-608/") -> str:
        """Build a minimal listing card with or without its public link."""
        link = f'href="{href}"' if href is not None else ""
        return (
            '<article class="rh_prop_card post-608">'
            f'<h3><a {link}>Casa de teste</a></h3>'
            '<div class="price">R$ 1.500</div></article>'
        )

    def test_search_parsers_normalize_property_links_and_preserve_identifiers(self) -> None:
        """Resolve absolute, relative, protocol-relative, and query identifier links."""
        cases = (
            ("https://marcioimoveis.net.br/imovel/apartamento-santa-terezinha/", "https://marcioimoveis.net.br/imovel/apartamento-santa-terezinha/"),
            ("/imovel/apartamento-santa-terezinha/", "https://marcioimoveis.net.br/imovel/apartamento-santa-terezinha/"),
            ("https://marcioimoveis.net.br/propriedade/casa-608/", "https://marcioimoveis.net.br/propriedade/casa-608/"),
            ("/propriedade/casa-608/", "https://marcioimoveis.net.br/propriedade/casa-608/"),
            ("//marcioimoveis.net.br/propriedade/casa-608/", "https://marcioimoveis.net.br/propriedade/casa-608/"),
            ("/propriedade/casa-608/?id=608", "https://marcioimoveis.net.br/propriedade/casa-608/?id=608"),
        )
        parsers = (CoreSearchPageParser(), SearchPageParser())

        for parser in parsers:
            for href, expected_url in cases:
                with self.subTest(parser=type(parser).__module__, href=href):
                    listing = parser.parse(self._card_html(href)).listings[0]
                    self.assertEqual(listing.to_dictionary()["url"], expected_url)

    def test_search_parsers_use_documented_post_id_fallback_when_href_is_missing(self) -> None:
        """Use the documented WordPress ID lookup only when a card ID exists."""
        parsers = (CoreSearchPageParser(), SearchPageParser())

        for parser in parsers:
            listing = parser.parse(self._card_html(None)).listings[0]
            self.assertEqual(
                listing.to_dictionary()["url"],
                "https://marcioimoveis.net.br/?post_type=property&p=608",
            )

    def test_search_parsers_reject_invalid_hosts_and_unrecoverable_missing_links(self) -> None:
        """Raise layer-local parser errors instead of returning untrusted or empty URLs."""
        cases = (
            ("https://example.org/property/608/", "foreign host"),
            ("/imoveis/?status=alugar", "search page"),
            ("/wp-content/uploads/property-608.jpg", "image asset"),
            (None, "unrecoverable"),
        )
        parser_expectations = (
            (CoreSearchPageParser(), CoreParserError),
            (SearchPageParser(), ParserError),
        )

        for parser, error_type in parser_expectations:
            for href, label in cases:
                with self.subTest(parser=type(parser).__module__, link=label):
                    card = self._card_html(href).replace("post-608", "")
                    with self.assertRaises(error_type):
                        parser.parse(card)

    def test_core_and_scripts_providers_forward_public_config_without_extra_calls(self) -> None:
        """Pass the configured public base to both parsers with one search request."""
        html = self._card_html("/propriedade/casa-608/?id=608")
        config = PortalConfiguration(base_url="https://public.example")
        core_config = CorePortalConfiguration(base_url="https://public.example")

        class ScriptTransport:
            def __init__(self) -> None:
                self.urls: list[str] = []

            def get(self, url: str, headers=None) -> HttpResponse:
                self.urls.append(url)
                return HttpResponse(200, html, url)

            def post(self, url: str, data: dict[str, str], headers=None) -> HttpResponse:
                self.urls.append(url)
                return HttpResponse(200, html, url)

        class CoreTransport:
            def __init__(self) -> None:
                self.urls: list[str] = []

            def get(self, url: str, headers=None) -> CoreHttpResponse:
                self.urls.append(url)
                return CoreHttpResponse(200, html, url)

            def post(self, url: str, data: dict[str, str], headers=None) -> CoreHttpResponse:
                self.urls.append(url)
                return CoreHttpResponse(200, html, url)

        script_transport = ScriptTransport()
        script_provider = MarcioRentalProvider(
            config,
            script_transport,
            SearchQueryBuilder(config),
            SearchPageParser(),
            PropertyDetailParser(),
            FacetParser(),
        )
        script_result = script_provider.search_rentals(RentalFilter())

        core_transport = CoreTransport()
        core_provider = CoreMarcioRentalProvider(
            core_config,
            core_transport,
            CoreSearchQueryBuilder(core_config),
            CoreSearchPageParser(),
            CorePropertyDetailParser(),
            CoreFacetParser(),
        )
        core_result = core_provider.search_rentals(RentalFilter())

        for result, transport in (
            (script_result, script_transport),
            (core_result, core_transport),
        ):
            self.assertEqual(
                result.to_dictionary()["listings"][0]["url"],
                "https://public.example/propriedade/casa-608/?id=608",
            )
            self.assertEqual(len(transport.urls), 1)

    def test_mcp_and_cli_expose_resolved_public_url(self) -> None:
        """Keep the same absolute URL through JSON serialization and CLI display."""
        html = self._card_html("/propriedade/casa-608/")
        result = SearchPageParser().parse(html)

        class StubProvider:
            def search_rentals(self, search_filter: RentalFilter):
                return result

        serialized = MarcioMcpAdapter(StubProvider()).search_rentals()
        output = StringIO()
        with redirect_stdout(output):
            run_search.display_results(serialized)

        self.assertEqual(
            serialized["listings"][0]["url"],
            "https://marcioimoveis.net.br/propriedade/casa-608/",
        )
        self.assertIn("URL: https://marcioimoveis.net.br/propriedade/casa-608/", output.getvalue())


class TestMcpAdapter(unittest.TestCase):
    """Test MCP tool adapter contract and outputs."""

    def setUp(self) -> None:
        self.adapter = MarcioMcpAdapter.create_default()

    def test_live_search(self) -> None:
        """Integration test executing real search."""
        res = self.adapter.search_rentals(bedrooms=2, page=1)
        self.assertIn("current_page", res)
        self.assertIn("max_pages", res)
        self.assertIn("total_properties", res)
        self.assertIn("listings", res)
        self.assertGreater(res["total_properties"], 0)

    def test_live_property_detail(self) -> None:
        """Integration test fetching real property detail."""
        detail = self.adapter.get_property_detail("RH-17772")
        self.assertIn("title", detail)
        self.assertIn("property_code", detail)
        self.assertIn("price", detail)
        self.assertIn("photos", detail)
        self.assertGreater(detail["photo_count"], 0)

    def test_live_facets(self) -> None:
        """Integration test fetching search facets."""
        facets = self.adapter.get_facets()
        self.assertIn("locations", facets)
        self.assertIn("property_types", facets)
        self.assertIn("statuses", facets)
        self.assertGreater(len(facets["locations"]), 0)


if __name__ == "__main__":
    unittest.main()
