#!/usr/bin/env python3
"""CLI runner executing rental search queries for Márcio Imóveis."""

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.client.configuration import PortalConfiguration
from scripts.domain.criteria import RentalFilter
from scripts.domain.value_objects import ListingPrice
from scripts.mcp.tools import MarcioMcpAdapter


def parse_arguments() -> argparse.Namespace:
    """Parse command line search arguments."""
    parser = argparse.ArgumentParser(description="Search rental properties on Márcio Imóveis.")
    parser.add_argument("--location", "-l", action="append", help="Location slug (can repeat)")
    parser.add_argument("--bedrooms", "-b", type=int, default=2, help="Number of bedrooms")
    parser.add_argument("--bathrooms", type=int, default=0, help="Number of bathrooms")
    parser.add_argument("--min-price", type=float, default=0.0, help="Minimum price ceiling")
    parser.add_argument("--max-price", type=float, default=0.0, help="Maximum price floor")
    parser.add_argument("--type", "-t", dest="property_type", default="", help="Property type slug")
    parser.add_argument("--sort", "-s", default="default", help="Sorting method (price-asc, price-desc, etc.)")
    parser.add_argument("--page", "-p", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    return parser.parse_args()


def display_results(result: dict) -> None:
    """Format and print search results to standard output."""
    print("=" * 70)
    print("MÁRCIO IMÓVEIS - RENTAL SEARCH RESULTS")
    print("=" * 70)
    print(f"Page: {result['current_page']} of {result['max_pages']}")
    print(f"Total matching properties: {result['total_properties']}")
    print(f"Properties on this page: {result['count_on_page']}")
    print(f"Has next page: {result['has_next_page']}")
    print("-" * 70)

    for idx, listing in enumerate(result["listings"], 1):
        print(f"[{idx}] {listing['title']}")
        print(f"    Code: {listing['property_code']}")
        print(f"    Price: {listing['price']}")
        print(f"    Bedrooms: {listing['bedrooms']} | Bathrooms: {listing['bathrooms']} | Garages: {listing['garages']}")
        print(f"    URL: {listing['url']}")
        if listing['thumbnail_url']:
            print(f"    Thumbnail: {listing['thumbnail_url']}")
        print()


def main() -> int:
    """Run search workflow."""
    args = parse_arguments()
    adapter = MarcioMcpAdapter.create_default()

    locations = args.location if args.location else None
    result = adapter.search_rentals(
        locations=locations,
        min_price=args.min_price,
        max_price=args.max_price,
        bedrooms=args.bedrooms,
        bathrooms=args.bathrooms,
        property_type=args.property_type,
        sort=args.sort,
        page=args.page,
    )

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    display_results(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
