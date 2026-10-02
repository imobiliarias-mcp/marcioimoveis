# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Subproject implementing a reverse-engineered rental search engine, scraper, and API client for **Márcio Imóveis** (`marcioimoveis.net.br`), a prominent real estate agency operating in Timóteo, Coronel Fabriciano, and Ipatinga (Vale do Aço, Minas Gerais, Brazil).

The codebase is engineered to plug into a Central Rental Research Model Context Protocol (MCP) server, structured as an installable Python package (`src/marcio_research/`) alongside an Object Calisthenics provider adapter and CLI suite (`scripts/`).

---

## Commands

### Environment Setup

The package supports Python >= 3.11 using `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

*Note: The CLI scripts in `scripts/` and test runner `scripts/run_tests.py` rely exclusively on Python standard library modules (`urllib.request`, `ssl`, `json`, `re`, `unittest`) and can run with standard `python3` without installing external dependencies.*

### Running Tests

```bash
# Standalone zero-dependency test runner (runs all unit and live integration tests)
python3 scripts/run_tests.py

# Run test suite via Python standard library unittest
python3 -m unittest discover tests

# Run a specific test class
python3 -m unittest tests.test_rental_research.TestValueObjects

# Run a single test method
python3 -m unittest tests.test_rental_research.TestValueObjects.test_property_code_valid

# Run tests via pytest (inside .venv)
pytest tests/test_rental_research.py
pytest tests/test_rental_research.py -k test_price_text_extractor
```

### Linting & Formatting

```bash
# Lint code with ruff
ruff check .

# Automatically apply safe fixes
ruff check --fix .
```

### Live CLI Utilities

```bash
# Search rentals by bedroom count and location
python3 scripts/run_search.py --location timoteo --bedrooms 2

# Search with price limits, sorting, and JSON output
python3 scripts/run_search.py --bedrooms 3 --min-price 1000 --max-price 2500 --sort price-asc --json

# Inspect property specifications and high-resolution photo gallery by reference code
python3 scripts/run_property_detail.py RH-17772

# Discover taxonomy facets (179 locations hierarchy, property types, statuses)
python3 scripts/run_facets.py
```

---

## High-Level Architecture & Structure

### Underlying SaaS Engine & Routing

- **Platform**: WordPress 6.x + **RealHomes Theme** (Modern variation) + **Easy Real Estate (ERE)** plugin.
- **Base Search URL**: `https://marcioimoveis.net.br/imoveis/`
- **Rental Filter Parameter**: `status=alugar`
- **Pagination Mechanics**: Canonical URL routing using slash-delimited page segments:
  - Page 1: `/imoveis/?status=alugar&...`
  - Page 2+: `/imoveis/page/{n}/?status=alugar&...`
- **Single Property Lookup**:
  - Direct URL: `https://marcioimoveis.net.br/propriedade/{slug}/`
  - ID Lookup fallback: `https://marcioimoveis.net.br/?post_type=property&p={numeric_id}`

### Critical Transport Constraints & Headers

> [!IMPORTANT]
> The target server runs Apache with **ModSecurity**. If the `Accept-Language` header is omitted, the web server immediately rejects the request with **HTTP 406 Not Acceptable**.

The HTTP transport layer (`UrllibTransport` in `scripts/client/http_transport.py` and `src/marcio_research/client/http_transport.py`) automatically enforces:
- `Accept-Language: pt-BR,pt;q=0.9,en;q=0.8` (mandatory)
- Desktop browser `User-Agent`
- Standard `Accept` and `Connection` headers
- Permissive SSL context handling

### Code Organization

```
marcioimoveis/
├── pyproject.toml                     # Hatchling build specification & dependencies (httpx, beautifulsoup4, pytest)
├── src/marcio_research/               # Installable library package
│   ├── interfaces/provider.py         # Protocols: RentalSearchCapability, RentalDetailCapability, RentalProviderProtocol
│   ├── domain/                        # Domain entities, value objects, criteria, collections, exceptions
│   ├── client/                        # Configuration, HTTP transport, query builder, parsers
│   ├── providers/marcio.py            # High-level MarcioRentalProvider implementation
│   └── mcp/tools.py                   # FastMCP tool adapter (marcio_search_rentals, marcio_get_property_detail, marcio_get_facets)
├── scripts/                           # Standalone Object Calisthenics CLI & provider adapter (standard library urllib)
│   ├── domain/                        # Calisthenics domain models, immutable criteria, and value objects
│   ├── client/                        # UrllibTransport, SearchQueryBuilder, SearchPageParser, PropertyDetailParser
│   ├── providers/marcio.py            # Calisthenics MarcioRentalProvider
│   ├── mcp/tools.py                   # FastMCP tool bindings
│   ├── run_search.py                  # CLI search execution tool
│   ├── run_property_detail.py         # CLI property detail inspection tool
│   ├── run_facets.py                  # CLI taxonomy facet explorer
│   └── run_tests.py                   # Standalone zero-dependency test runner
├── tests/
│   └── test_rental_research.py        # Comprehensive unit and live integration test suite
└── docs/
    ├── api-research.md                # Reverse-engineered API specification and query matrix
    ├── README.md                      # Documentation index
    └── sot/                           # Single Source of Truth contracts
```

### Object Calisthenics Rules (`scripts/` and `src/`)

All code strictly enforces Object Calisthenics and Clean Architecture standards:
1. **One indent level per method**: Complex branching is extracted into helper methods.
2. **No `else` keyword**: Uses guard clauses and early returns exclusively.
3. **Wrapped primitives**: Domain concepts are wrapped into strong value objects:
   - `ListingPrice`: Monetary amounts and BRL currency formatting.
   - `PropertyCode`: Validated alphanumeric reference codes (e.g., `RH-17772`).
   - `LocationSlug`: Normalized lowercase slug representations.
   - `RoomCount`: Non-negative bedroom/bathroom integer quantities.
4. **First-class collections**: `ListingCollection`, `PhotoCollection`, and `FacetOptionCollection` encapsulate lists without exposing state.
5. **Small entities**: Classes ≤ 100 lines, functions ≤ 15 lines, modules < 200 lines.
6. **≤ 2 instance variables per class**: Classes are composed of small, focused collaborator objects.
7. **No public getters/setters**: Exposes behavior or `.to_dict()` serialization.
