#!/usr/bin/env python3
"""CLI runner extracting available search facets from Márcio Imóveis."""

import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.mcp.tools import MarcioMcpAdapter


def parse_arguments() -> argparse.Namespace:
    """Parse command line facet arguments."""
    parser = argparse.ArgumentParser(description="Extract taxonomy facets from Márcio Imóveis.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    return parser.parse_args()


def display_facets(facets: dict) -> None:
    """Format and print facet catalogs to standard output."""
    print("=" * 70)
    print("MÁRCIO IMÓVEIS - SEARCH FACETS & TAXONOMIES")
    print("=" * 70)

    print(f"Top-level Location Nodes: {len(facets['locations'])}")
    for loc in facets["locations"][:10]:
        print(f"  - [{loc['term_id']}] {loc['name']} (slug: {loc['slug']}) -> {loc['count']} listings")
        for child in loc.get("children", [])[:3]:
            print(f"      * [{child['term_id']}] {child['name']} (slug: {child['slug']}) -> {child['count']} listings")
    if len(facets["locations"]) > 10:
        print(f"  ... and {len(facets['locations']) - 10} more top-level locations.")

    print("-" * 70)
    print(f"Property Types ({len(facets['property_types'])} types):")
    for pt in facets["property_types"]:
        print(f"  - {pt['name']} (slug: {pt['slug']})")

    print("-" * 70)
    print("Transaction Statuses:")
    for st in facets["statuses"]:
        print(f"  - {st['name']} (slug: {st['slug']})")
    print("=" * 70)


def main() -> int:
    """Execute facet extraction workflow."""
    args = parse_arguments()
    adapter = MarcioMcpAdapter.create_default()

    facets = adapter.get_facets()
    if args.json:
        print(json.dumps(facets, indent=2, ensure_ascii=False))
        return 0

    display_facets(facets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
