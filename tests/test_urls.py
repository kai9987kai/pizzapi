try:
    from urllib.parse import urlparse
except ImportError:  # pragma: no cover - Python 2
    from urlparse import urlparse

import pytest

from pizzapy.exceptions import InvalidCountryError, PizzaPyError
from pizzapy.urls import COUNTRIES, COUNTRY_CANADA, COUNTRY_USA, Urls, validate_country

GETTERS = (
    'find_url', 'info_url', 'menu_url', 'place_url', 'price_url',
    'validate_url', 'coupon_url', 'track_by_order', 'track_by_phone',
)


TLDS = {COUNTRY_USA: '.com', COUNTRY_CANADA: '.ca'}


@pytest.mark.parametrize('country', COUNTRIES)
@pytest.mark.parametrize('getter', GETTERS)
def test_every_getter_returns_an_https_url_for_its_country(country, getter):
    url = getattr(Urls(country), getter)()
    parsed = urlparse(url)
    assert parsed.scheme == 'https'
    assert parsed.hostname.endswith('dominos' + TLDS[country]), parsed.hostname


@pytest.mark.parametrize('getter', GETTERS)
def test_canadian_urls_use_the_canadian_domain(getter):
    assert '.ca/' in getattr(Urls(COUNTRY_CANADA), getter)()
    assert '.com/' in getattr(Urls(COUNTRY_USA), getter)()


def test_tracking_uses_the_tracker_host():
    assert Urls().track_by_phone().startswith('https://trkweb.dominos.com/')
    assert Urls(COUNTRY_CANADA).track_by_order().startswith('https://trkweb.dominos.ca/')


def test_order_host_and_referer_follow_the_country():
    assert Urls().order_host == 'order.dominos.com'
    assert Urls(COUNTRY_CANADA).order_host == 'order.dominos.ca'
    assert Urls(COUNTRY_CANADA).referer == 'https://order.dominos.ca/en/pages/order/'


def test_unsupported_country_is_rejected_immediately():
    """An unsupported country used to be accepted, then fail with a KeyError."""
    with pytest.raises(InvalidCountryError) as excinfo:
        Urls('uk')
    assert 'uk' in str(excinfo.value)


def test_invalid_country_error_is_a_value_error_and_a_pizzapy_error():
    assert issubclass(InvalidCountryError, ValueError)
    assert issubclass(InvalidCountryError, PizzaPyError)


def test_validate_country_returns_the_country():
    assert validate_country(COUNTRY_CANADA) == COUNTRY_CANADA
