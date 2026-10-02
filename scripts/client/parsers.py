"""Specialized parsers extracting domain entities from HTML and JSON payloads."""

import json
import re
from bs4 import BeautifulSoup, Tag

from scripts.domain.collections import FacetOptionCollection, ListingCollection, PhotoCollection
from scripts.domain.entities import (
    FacetCatalog,
    FacetOption,
    PropertyDetail,
    RentalListing,
    SearchPageResult,
)
from scripts.domain.exceptions import ParserError, PropertyNotFoundError
from scripts.domain.value_objects import ListingPrice, PropertyCode


class PriceTextExtractor:
    """Extracts numeric price from Brazilian currency string."""

    @staticmethod
    def extract(price_str: str) -> ListingPrice | None:
        """Parse price text such as 'R$ 1.150', 'R$1,150', or 'R$ 1.150,00' into ListingPrice."""
        if not price_str:
            return None
        cleaned = re.sub(r"[^\d,\.]", "", price_str).strip()
        if not cleaned:
            return None
        # Pattern 1: Brazilian standard "1.150,00"
        if re.search(r"\.\d{3},\d{2}$", cleaned):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Pattern 2: English standard "1,150.00"
        elif re.search(r",\d{3}\.\d{2}$", cleaned):
            cleaned = cleaned.replace(",", "")
        # Pattern 3: Thousands without decimals "1,150" or "1.150"
        elif re.search(r"[,.]\d{3}$", cleaned):
            cleaned = re.sub(r"[,.]", "", cleaned)
        # Pattern 4: Decimals only "150,50"
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            val = float(cleaned)
            return ListingPrice(val)
        except ValueError:
            return None


class SearchPageParser:
    """Parses search results page into SearchPageResult entity."""

    def parse(self, html: str) -> SearchPageResult:
        """Extract listings and pagination stats from search HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            stats = self._extract_stats(soup)
            listings = self._extract_listings(soup)
            has_next = stats["current_page"] < stats["max_pages"]
            return SearchPageResult(
                listings=ListingCollection(listings),
                current_page=stats["current_page"],
                max_pages=stats["max_pages"],
                total_properties=stats["total_properties"],
                has_next_page=has_next,
            )
        except Exception as exc:
            msg = f"Failed parsing search page HTML: {exc}"
            raise ParserError(msg) from exc

    def _extract_stats(self, soup: BeautifulSoup) -> dict[str, int]:
        """Extract pagination indicators from stats container."""
        stats_el = soup.select_one(".rh_pagination__stats")
        if not stats_el:
            return {"current_page": 1, "max_pages": 1, "total_properties": 0}
        curr = int(stats_el.get("data-page", 1))
        max_p = int(stats_el.get("data-max", 1))
        tot = int(stats_el.get("data-total-properties", 0))
        return {"current_page": curr, "max_pages": max_p, "total_properties": tot}

    def _extract_listings(self, soup: BeautifulSoup) -> list[RentalListing]:
        """Extract listing cards from DOM."""
        cards = soup.select("article.rh_prop_card, article.rh_list_card, article")
        results: list[RentalListing] = []
        for card in cards:
            listing = self._parse_card(card)
            if listing:
                results.append(listing)
        return results

    def _parse_card(self, card: Tag) -> RentalListing | None:
        """Parse individual property card element."""
        title_el = card.select_one("h3 a, .rh_prop_card__title a, .rh_list_card__title a")
        if not title_el:
            return None
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")

        price_el = card.select_one(".rh_prop_card__price, .rh_list_card__price, .price")
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = PriceTextExtractor.extract(price_text)

        meta_items = [m.get_text(strip=True) for m in card.select(".rh_prop_card__meta, .rh_list_card__meta")]
        bedrooms = self._extract_int(meta_items, r"Quartos?\s*(\d+)")
        bathrooms = self._extract_int(meta_items, r"Banheiros?\s*(\d+)")
        garages = self._extract_int(meta_items, r"Garag(?:em|ens)?\s*(\d+)")

        thumb = self._extract_thumbnail(card)
        code_str = self._extract_code(card, url)

        return RentalListing(
            title=title,
            property_code=PropertyCode(code_str),
            url=url,
            price=price,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            garages=garages,
            thumbnail_url=thumb,
            raw_meta=meta_items,
        )

    def _extract_thumbnail(self, card: Tag) -> str:
        """Extract thumbnail image URL from card."""
        img = card.select_one("img")
        if img and img.get("src"):
            return img["src"]
        style_el = card.select_one(".post_thumbnail")
        if style_el and style_el.get("style"):
            m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", style_el["style"])
            if m:
                return m.group(1)
        return ""

    def _extract_code(self, card: Tag, url: str) -> str:
        """Derive property code from URL or card classes."""
        code_el = card.select_one(".rh_prop_card__meta_id, .property-id")
        if code_el:
            return code_el.get_text(strip=True)
        for cls in card.get("class", []):
            if cls.startswith("post-"):
                return cls.replace("post-", "RH-")
        # Extract from URL slug
        parts = [p for p in url.strip("/").split("/") if p]
        if parts:
            return parts[-1]
        return "UNKNOWN"

    def _extract_int(self, items: list[str], pattern: str) -> int:
        """Extract numeric value matching regex pattern across strings."""
        for item in items:
            m = re.search(pattern, item, re.I)
            if m:
                return int(m.group(1))
        return 0


class PropertyDetailParser:
    """Parses individual property detail page HTML into PropertyDetail entity."""

    def parse(self, html: str, url: str) -> PropertyDetail:
        """Extract full specifications, photos, and descriptions from page."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            if "Nenhum Resultado Encontrado" in html and not soup.select_one("article"):
                raise PropertyNotFoundError(f"Property at {url} was not found.")

            title = self._extract_title(soup)
            code = self._extract_code(soup, url)
            price = self._extract_price(soup)
            desc = self._extract_description(soup)
            photos = self._extract_photos(soup)
            map_data = self._extract_map_data(html)
            meta_dict = self._extract_meta_specs(soup)

            return PropertyDetail(
                title=title,
                property_code=PropertyCode(code),
                url=url,
                price=price,
                status=meta_dict.get("status", "Para Alugar"),
                property_type=meta_dict.get("property_type", "Imóvel"),
                bedrooms=meta_dict.get("bedrooms", 0),
                bathrooms=meta_dict.get("bathrooms", 0),
                garages=meta_dict.get("garages", 0),
                description=desc,
                photos=PhotoCollection(photos),
                map_data=map_data,
                address=meta_dict.get("address", ""),
            )
        except PropertyNotFoundError:
            raise
        except Exception as exc:
            msg = f"Failed parsing property detail from {url}: {exc}"
            raise ParserError(msg) from exc

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract cleaned property title."""
        title_el = soup.select_one("h1.rh_page__title, .entry-title")
        if title_el:
            return title_el.get_text(strip=True)
        if soup.title:
            return soup.title.get_text(strip=True).split("–")[0].strip()
        return "Imóvel"

    def _extract_code(self, soup: BeautifulSoup, url: str) -> str:
        """Extract property reference code (e.g. RH-17772)."""
        text = soup.get_text()
        m = re.search(r"Cod\.\s*do\s*Im[oó]vel\s*:\s*([A-Za-z0-9_-]+)", text, re.I)
        if m:
            return m.group(1).strip()
        slug_match = re.search(r"/imovel/([^/]+)/?", url)
        if slug_match:
            return slug_match.group(1)
        return "RH-PROPERTY"

    def _extract_price(self, soup: BeautifulSoup) -> ListingPrice | None:
        """Extract price from page header."""
        price_el = soup.select_one(".price, .rh_page__head .price")
        if price_el:
            return PriceTextExtractor.extract(price_el.get_text(strip=True))
        return None

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract textual description of the property."""
        desc_el = soup.select_one(".rh_content, .rh_property__content, .entry-content")
        if desc_el:
            return desc_el.get_text(separator="\n", strip=True)
        return ""

    def _extract_photos(self, soup: BeautifulSoup) -> list[str]:
        """Extract high-resolution photo URLs."""
        urls: set[str] = set()
        for a in soup.select("a[data-fancybox], a[href*='/wp-content/uploads/']"):
            href = a.get("href", "")
            if href.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                urls.add(href)
        for img in soup.select(".rh_property__gallery img, .rh_gallery__item img"):
            src = img.get("src", "")
            if src.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                urls.add(src)
        return sorted(urls)

    def _extract_map_data(self, html: str) -> dict:
        """Extract propertyMapData script configuration."""
        matches = re.findall(r"propertyMapData\s*=\s*({[^;]+});", html)
        for m in matches:
            try:
                data = json.loads(m)
                if "lat" in data and "lng" in data:
                    return data
            except Exception:
                continue
        return {}

    def _extract_meta_specs(self, soup: BeautifulSoup) -> dict:
        """Extract bedrooms, bathrooms, and garages from specs rows."""
        specs = {"bedrooms": 0, "bathrooms": 0, "garages": 0, "status": "Para Alugar", "property_type": "Imóvel"}
        text = soup.get_text()
        bed_m = re.search(r"Quartos?\s*[:\n\r]*\s*(\d+)", text, re.I)
        if bed_m:
            specs["bedrooms"] = int(bed_m.group(1))
        bath_m = re.search(r"Banheiros?\s*[:\n\r]*\s*(\d+)", text, re.I)
        if bath_m:
            specs["bathrooms"] = int(bath_m.group(1))
        gar_m = re.search(r"Garag(?:em|ens)?\s*[:\n\r]*\s*(\d+)", text, re.I)
        if gar_m:
            specs["garages"] = int(gar_m.group(1))
        # Status / Type from breadcrumbs
        breadcrumbs = soup.select(".rh_breadcrumbs a, .breadcrumbs a")
        if len(breadcrumbs) >= 2:
            specs["property_type"] = breadcrumbs[1].get_text(strip=True)
        return specs


class FacetParser:
    """Parses realhomesLocationsData and search form select elements into FacetCatalog."""

    def parse(self, html: str) -> FacetCatalog:
        """Extract taxonomy facets, locations tree, and select options."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            locations = self._extract_locations(html)
            types = self._extract_select_options(soup, "type[]")
            statuses = self._extract_select_options(soup, "status")
            return FacetCatalog(
                locations=FacetOptionCollection(locations),
                property_types=FacetOptionCollection(types),
                statuses=FacetOptionCollection(statuses),
            )
        except Exception as exc:
            msg = f"Failed parsing facets from HTML: {exc}"
            raise ParserError(msg) from exc

    def _extract_locations(self, html: str) -> list[FacetOption]:
        """Extract hierarchical locations from realhomesLocationsData JS variable."""
        matches = re.findall(r"var\s+realhomesLocationsData\s*=\s*({.*?});", html, re.DOTALL)
        if not matches:
            return []
        data = json.loads(matches[0])
        raw_locs = data.get("all_locations", [])
        return [self._build_location_node(loc) for loc in raw_locs]

    def _build_location_node(self, item: dict) -> FacetOption:
        """Recursively construct FacetOption tree."""
        children = [self._build_location_node(c) for c in item.get("children", [])]
        return FacetOption(
            name=item.get("name", ""),
            slug=item.get("slug", ""),
            count=item.get("count", 0),
            term_id=item.get("term_id", 0),
            children=children,
        )

    def _extract_select_options(self, soup: BeautifulSoup, select_name: str) -> list[FacetOption]:
        """Extract options from named select tag."""
        select_el = soup.find("select", attrs={"name": select_name})
        if not select_el:
            return []
        options: list[FacetOption] = []
        for opt in select_el.find_all("option"):
            val = opt.get("value", "")
            if val and val != "any":
                options.append(FacetOption(name=opt.get_text(strip=True), slug=val))
        return options
