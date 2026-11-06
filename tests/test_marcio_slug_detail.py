"""Detail requests for Márcio listing slugs go straight to the public /imovel/<slug>/ page."""

from contextlib import suppress

from scripts.client.configuration import PortalConfiguration
from scripts.client.http_transport import HttpResponse
from scripts.client.parsers import FacetParser, PropertyDetailParser, SearchPageParser
from scripts.client.query_builder import SearchQueryBuilder
from scripts.domain.value_objects import PropertyCode
from scripts.providers.marcio import MarcioRentalProvider

BASE_URL = "https://marcioimoveis.net.br"


class RecordingTransport:
    """Records requested URLs and answers every request with an empty page."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def get(self, url: str, headers=None) -> HttpResponse:
        self.urls.append(url)
        return HttpResponse(200, "<html></html>", url)

    def post(self, url: str, data, headers=None) -> HttpResponse:
        self.urls.append(url)
        return HttpResponse(200, "<html></html>", url)


def _provider(transport: RecordingTransport) -> MarcioRentalProvider:
    config = PortalConfiguration(base_url=BASE_URL)
    return MarcioRentalProvider(
        config,
        transport,
        SearchQueryBuilder(config),
        SearchPageParser(),
        PropertyDetailParser(),
        FacetParser(),
    )


def test_slug_code_requests_public_imovel_page_without_searching():
    transport = RecordingTransport()
    with suppress(Exception):
        _provider(transport).get_property_detail(PropertyCode("apartamento-eldorado"))
    assert transport.urls == [f"{BASE_URL}/imovel/apartamento-eldorado/"]


def test_numeric_code_still_resolves_through_property_search():
    transport = RecordingTransport()
    with suppress(Exception):
        _provider(transport).get_property_detail(PropertyCode("608"))
    assert len(transport.urls) == 2
    assert transport.urls[0].startswith(BASE_URL)
