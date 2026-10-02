"""Unit and integration test suite for Márcio Imóveis rental research modules."""

import unittest

from scripts.client.configuration import PortalConfiguration
from scripts.client.parsers import FacetParser, PriceTextExtractor, PropertyDetailParser, SearchPageParser
from scripts.client.query_builder import SearchQueryBuilder
from scripts.domain.collections import FacetOptionCollection, ListingCollection, PhotoCollection
from scripts.domain.criteria import RentalFilter
from scripts.domain.entities import RentalListing
from scripts.domain.exceptions import InvalidFilterError, PropertyNotFoundError
from scripts.domain.value_objects import ListingPrice, LocationSlug, PropertyCode, RoomCount
from scripts.mcp.tools import MarcioMcpAdapter


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
