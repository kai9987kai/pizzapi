from .exceptions import InvalidCountryError

COUNTRY_USA = 'us'
COUNTRY_CANADA = 'ca'

#: Every country this library knows how to talk to.
COUNTRIES = (COUNTRY_USA, COUNTRY_CANADA)

#: Per-country hosts. The ordering API and the tracker live on different
#: hosts, and Domino's runs a separate top-level domain per country.
_HOSTS = {
    COUNTRY_USA: {'order': 'order.dominos.com', 'track': 'trkweb.dominos.com'},
    COUNTRY_CANADA: {'order': 'order.dominos.ca', 'track': 'trkweb.dominos.ca'},
}

#: Endpoint paths, shared by every country. ``{order}`` and ``{track}`` are
#: filled in with the country's hosts; the remaining placeholders are filled
#: in by the caller (see :func:`pizzapy.utils.request_json`).
_PATHS = {
    'find_url': 'https://{order}/power/store-locator?s={{line1}}&c={{line2}}&type={{type}}',
    'info_url': 'https://{order}/power/store/{{store_id}}/profile',
    'menu_url': 'https://{order}/power/store/{{store_id}}/menu?lang={{lang}}&structured=true',
    'place_url': 'https://{order}/power/place-order',
    'price_url': 'https://{order}/power/price-order',
    'validate_url': 'https://{order}/power/validate-order',
    'coupon_url': 'https://{order}/power/store/{{store_id}}/coupon/{{couponid}}?lang={{lang}}',
    'track_by_order': 'https://{track}/orderstorage/GetTrackerData?StoreID={{store_id}}&OrderKey={{order_key}}',
    'track_by_phone': 'https://{track}/orderstorage/GetTrackerData?Phone={{phone}}',
}


def _build_urls(country):
    hosts = _HOSTS[country]
    return {name: path.format(**hosts) for name, path in _PATHS.items()}


def validate_country(country):
    """Return ``country`` if it is supported, otherwise raise.

    Raises:
        InvalidCountryError: If ``country`` is not one of :data:`COUNTRIES`.
    """
    if country not in _HOSTS:
        raise InvalidCountryError(
            'unsupported country {!r}: expected one of {}'.format(
                country, ', '.join(repr(c) for c in COUNTRIES)
            )
        )
    return country


class Urls(object):
    """URLs for doing different things to the API.

    This holds the country-unique information on how to interact with the
    API, plus getter methods for reaching it. Those getters are handy to pass
    as a first argument to :func:`pizzapy.utils.request_json` /
    :func:`pizzapy.utils.request_xml`.

    Attributes:
        country (str): The country this instance is bound to.
        urls (dict): Every country's URL table, keyed by country code.

    Raises:
        InvalidCountryError: If ``country`` is not supported. Previously an
            unsupported country was accepted here and failed much later with
            an opaque ``KeyError``.
    """

    def __init__(self, country=COUNTRY_USA):
        self.country = validate_country(country)
        self.urls = {c: _build_urls(c) for c in COUNTRIES}

    def __repr__(self):
        return 'Urls for {}'.format(self.country)

    @property
    def order_host(self):
        """The ordering host for this country, e.g. ``order.dominos.com``."""
        return _HOSTS[self.country]['order']

    @property
    def referer(self):
        """The ``Referer`` header the ordering endpoints expect."""
        return 'https://{}/en/pages/order/'.format(self.order_host)

    def find_url(self):
        return self.urls[self.country]['find_url']

    def info_url(self):
        return self.urls[self.country]['info_url']

    def menu_url(self):
        return self.urls[self.country]['menu_url']

    def place_url(self):
        return self.urls[self.country]['place_url']

    def price_url(self):
        return self.urls[self.country]['price_url']

    def track_by_order(self):
        return self.urls[self.country]['track_by_order']

    def track_by_phone(self):
        return self.urls[self.country]['track_by_phone']

    def validate_url(self):
        return self.urls[self.country]['validate_url']

    def coupon_url(self):
        return self.urls[self.country]['coupon_url']
