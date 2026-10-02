#!/usr/bin/env python3
"""Comprehensive test runner for Márcio Imóveis rental research module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest

from scripts.client.configuration import PortalConfiguration
from scripts.client.parsers import PriceTextExtractor, SearchPageParser
from scripts.client.query_builder import SearchQueryBuilder
from scripts.domain.criteria import RentalFilter
from scripts.domain.exceptions import InvalidFilterError
from scripts.domain.value_objects import (
    ListingPrice,
    LocationSlug,
    PropertyCode,
    RoomCount,
)
from scripts.mcp.tools import MarcioMcpAdapter


class TestValueObjects(unittest.TestCase):
    """Unit tests for domain value objects."""

    def test_property_code_valid(self) -> None:
        code = PropertyCode(" RH-17772 ")
        self.assertEqual(str(code), "RH-17772")
        self.assertEqual(code.numeric_id(), "17772")

    def test_property_code_empty_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            PropertyCode("   ")

    def test_listing_price_valid(self) -> None:
        price = ListingPrice(1150.0)
        self.assertEqual(price.amount, 1150.0)
        self.assertEqual(price.to_integer(), 1150)
        self.assertIn("1.150,00", price.format_brl())

    def test_listing_price_negative_fails(self) -> None:
        with self.assertRaises(InvalidFilterError):
            ListingPrice(-10.0)

    def test_location_slug_valid(self) -> None:
        slug = LocationSlug(" Timoteo ")
        self.assertEqual(str(slug), "timoteo")

    def test_room_count_valid(self) -> None:
        rc = RoomCount(2)
        self.assertEqual(int(rc), 2)


class TestRentalFilter(unittest.TestCase):
    """Unit tests for criteria builder and immutability."""

    def test_default_filter(self) -> None:
        rf = RentalFilter()
        self.assertEqual(rf.status, "alugar")
        self.assertEqual(rf.page, 1)

    def test_filter_immutability(self) -> None:
        rf1 = RentalFilter()
        rf2 = rf1.with_bedrooms(2).with_location("timoteo").with_page(2)
        self.assertEqual(rf1.page, 1)
        self.assertIsNone(rf1.bedrooms)
        self.assertEqual(rf2.page, 2)
        self.assertEqual(int(rf2.bedrooms), 2)
        self.assertEqual(str(rf2.locations[0]), "timoteo")


class TestQueryBuilder(unittest.TestCase):
    """Unit tests for search query builder."""

    def setUp(self) -> None:
        self.config = PortalConfiguration()
        self.builder = SearchQueryBuilder(self.config)

    def test_page_one_url(self) -> None:
        rf = RentalFilter().with_bedrooms(2).with_location("timoteo")
        url = self.builder.build_search_url(rf)
        self.assertTrue(url.startswith("https://marcioimoveis.net.br/properties-search/?"))
        self.assertIn("location%5B%5D=timoteo", url)
        self.assertIn("bedrooms=2", url)
        self.assertIn("status=alugar", url)

    def test_page_two_url_path(self) -> None:
        rf = RentalFilter().with_page(2).with_bedrooms(2)
        url = self.builder.build_search_url(rf)
        self.assertIn("/properties-search/page/2/?", url)


class TestParsers(unittest.TestCase):
    """Unit tests for HTML parsers."""

    def test_price_text_extractor(self) -> None:
        p1 = PriceTextExtractor.extract("R$1,150")
        self.assertIsNotNone(p1)
        self.assertEqual(p1.amount, 1150.0)

        p2 = PriceTextExtractor.extract("R$ 2.930,00")
        self.assertIsNotNone(p2)
        self.assertEqual(p2.amount, 2930.0)

        p3 = PriceTextExtractor.extract("invalid")
        self.assertIsNone(p3)

    def test_search_page_parser_empty(self) -> None:
        html = '<div class="rh_pagination__stats" data-page="1" data-max="1" data-total-properties="0"></div>'
        parser = SearchPageParser()
        result = parser.parse(html)
        self.assertEqual(result.total_properties, 0)
        self.assertEqual(len(result.listings), 0)
        self.assertFalse(result.has_next_page)


class TestLiveIntegration(unittest.TestCase):
    """Live verification tests against marcioimoveis.net.br."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = MarcioMcpAdapter.create_default()

    def test_live_rental_search(self) -> None:
        """Verify rental search reproducing target query."""
        res = self.adapter.search_rentals(bedrooms=2, page=1)
        self.assertGreater(res["total_properties"], 0)
        self.assertGreater(res["count_on_page"], 0)
        self.assertIsInstance(res["listings"], list)
        first = res["listings"][0]
        self.assertTrue(len(first["title"]) > 0)
        self.assertTrue(first["url"].startswith("http"))

    def test_live_property_detail(self) -> None:
        """Verify property detail retrieval."""
        detail = self.adapter.get_property_detail("RH-17772")
        self.assertIn("17772", detail["property_code"])
        self.assertTrue(len(detail["title"]) > 0)
        self.assertGreater(detail["photo_count"], 0)

    def test_live_facets(self) -> None:
        """Verify facet extraction containing top locations and types."""
        facets = self.adapter.get_facets()
        self.assertGreater(len(facets["locations"]), 0)
        self.assertGreater(len(facets["property_types"]), 0)
        self.assertGreater(len(facets["statuses"]), 0)


def main() -> int:
    """Run test suite."""
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
