#!/usr/bin/env python3
"""CLI runner retrieving complete property details for Márcio Imóveis."""

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.mcp.tools import MarcioMcpAdapter


def parse_arguments() -> argparse.Namespace:
    """Parse command line property arguments."""
    parser = argparse.ArgumentParser(description="Retrieve property detail on Márcio Imóveis.")
    parser.add_argument(
        "property_code",
        nargs="?",
        default="RH-17772",
        help="Property reference code (e.g. RH-17772 or URL slug)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    return parser.parse_args()


def display_detail(detail: dict) -> None:
    """Format and print property detail to standard output."""
    print("=" * 70)
    print(f"PROPERTY DETAIL: {detail['title']}")
    print("=" * 70)
    print(f"Reference Code: {detail['property_code']}")
    print(f"Transaction:    {detail['status']}")
    print(f"Property Type:  {detail['property_type']}")
    print(f"Price:          {detail['price']}")
    print(f"Bedrooms:       {detail['bedrooms']}")
    print(f"Bathrooms:      {detail['bathrooms']}")
    print(f"Garages:        {detail['garages']}")
    print(f"URL:            {detail['url']}")
    if detail['map_data']:
        lat = detail['map_data'].get('lat')
        lng = detail['map_data'].get('lng')
        print(f"Coordinates:    lat={lat}, lng={lng}")

    print("-" * 70)
    print(f"Photos ({detail['photo_count']} images):")
    for idx, photo_url in enumerate(detail["photos"][:5], 1):
        print(f"  [{idx}] {photo_url}")
    if detail["photo_count"] > 5:
        print(f"  ... and {detail['photo_count'] - 5} more photos.")

    print("-" * 70)
    print("Description:")
    print(detail["description"][:400] + ("..." if len(detail["description"]) > 400 else ""))
    print("=" * 70)


def main() -> int:
    """Execute property retrieval."""
    args = parse_arguments()
    adapter = MarcioMcpAdapter.create_default()

    detail = adapter.get_property_detail(args.property_code)
    if args.json:
        print(json.dumps(detail, indent=2, ensure_ascii=False))
        return 0

    display_detail(detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())
