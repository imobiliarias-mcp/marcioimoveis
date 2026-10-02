# Márcio Imóveis — Rental Search MCP Research & Client

Reverse-engineered rental search integration and client modules for **Márcio Imóveis** (`marcioimoveis.net.br`), engineered for the central rental research MCP.

## Key Features
- **Stateless Search Engine**: Canonical SEO URL generation matching the WordPress RealHomes / ERE router conventions.
- **Full Filter Support**: 179 locations hierarchy, property types, bedrooms, bathrooms, price range, sorting, and pagination.
- **Property Detail Extraction**: Comprehensive extraction of property titles, internal IDs, reference codes, descriptions, amenities, geo coordinates, and high-resolution photo URLs.
- **Taxonomy & Locations Catalog**: Integration with `realhomesLocationsData` exposing 179 cities and neighborhoods.
- **Clean Architecture**: Adheres strictly to SOLID, Object Calisthenics (no else, wrapped primitives, small entities), and Hexagonal design.
- **Resilient Transport**: Automatically handles server-level ModSecurity Content Negotiation requirements (`Accept-Language`) preventing HTTP 406 errors.

## Quick Start

### 1. Run Search CLI
```bash
python3 scripts/run_search.py --bedrooms 2
python3 scripts/run_search.py --location timoteo --bedrooms 2
```

### 2. View Property Details CLI
```bash
python3 scripts/run_property_detail.py RH-17772
```

### 3. Query Facets CLI
```bash
python3 scripts/run_facets.py
```

### 4. Run Test Suite
```bash
# Standalone test runner
python3 scripts/run_tests.py

# Unittest discover
python3 -m unittest discover tests
```

## Documentation
- [API Research & Specification](docs/api-research.md)
- [Research Plan & Report](scripts/research-plan.md)
