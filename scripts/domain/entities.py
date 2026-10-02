"""Domain entities representing rental listings, details, and search results."""

from dataclasses import dataclass, field

from scripts.domain.collections import FacetOptionCollection, ListingCollection, PhotoCollection
from scripts.domain.value_objects import ListingPrice, PropertyCode


@dataclass
class RentalListing:
    """Represents a rental property item from search listing cards."""

    title: str
    property_code: PropertyCode
    url: str
    price: ListingPrice | None
    bedrooms: int = 0
    bathrooms: int = 0
    garages: int = 0
    neighborhood: str = ""
    city: str = ""
    thumbnail_url: str = ""
    raw_meta: list[str] = field(default_factory=list)

    def to_dictionary(self) -> dict:
        """Convert entity to serializable dictionary."""
        return {
            "title": self.title,
            "property_code": str(self.property_code),
            "url": self.url,
            "price": self.price.format_brl() if self.price else None,
            "price_amount": self.price.amount if self.price else None,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "garages": self.garages,
            "neighborhood": self.neighborhood,
            "city": self.city,
            "thumbnail_url": self.thumbnail_url,
            "raw_meta": list(self.raw_meta),
        }


@dataclass
class PropertyDetail:
    """Represents complete property detail retrieved from single property page."""

    title: str
    property_code: PropertyCode
    url: str
    price: ListingPrice | None
    status: str
    property_type: str
    bedrooms: int = 0
    bathrooms: int = 0
    garages: int = 0
    description: str = ""
    photos: PhotoCollection = field(default_factory=PhotoCollection)
    map_data: dict = field(default_factory=dict)
    address: str = ""

    def to_dictionary(self) -> dict:
        """Convert entity to serializable dictionary."""
        return {
            "title": self.title,
            "property_code": str(self.property_code),
            "url": self.url,
            "price": self.price.format_brl() if self.price else None,
            "price_amount": self.price.amount if self.price else None,
            "status": self.status,
            "property_type": self.property_type,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "garages": self.garages,
            "description": self.description,
            "photos": self.photos.to_list(),
            "photo_count": len(self.photos),
            "map_data": dict(self.map_data),
            "address": self.address,
        }


@dataclass
class SearchPageResult:
    """Represents paginated rental search response."""

    listings: ListingCollection
    current_page: int
    max_pages: int
    total_properties: int
    has_next_page: bool

    def to_dictionary(self) -> dict:
        """Convert result to serializable dictionary."""
        return {
            "current_page": self.current_page,
            "max_pages": self.max_pages,
            "total_properties": self.total_properties,
            "has_next_page": self.has_next_page,
            "count_on_page": len(self.listings),
            "listings": self.listings.to_list(),
        }


@dataclass
class FacetOption:
    """Represents an individual filter option."""

    name: str
    slug: str
    count: int = 0
    term_id: int = 0
    children: list["FacetOption"] = field(default_factory=list)

    def to_dictionary(self) -> dict:
        """Convert facet option to dictionary."""
        return {
            "name": self.name,
            "slug": self.slug,
            "count": self.count,
            "term_id": self.term_id,
            "children": [child.to_dictionary() for child in self.children],
        }


@dataclass
class FacetCatalog:
    """Represents available search facets and taxonomy options."""

    locations: FacetOptionCollection
    property_types: FacetOptionCollection
    statuses: FacetOptionCollection

    def to_dictionary(self) -> dict:
        """Convert catalog to dictionary."""
        return {
            "locations": self.locations.to_list(),
            "property_types": self.property_types.to_list(),
            "statuses": self.statuses.to_list(),
        }
