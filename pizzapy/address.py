from .exceptions import InvalidAddressError, StoreNotFoundError
from .store import Store
from .utils import request_json, looks_like_postal_code
from .urls import Urls, COUNTRY_USA, validate_country


class Address(object):
    """Create an address, for finding stores and placing orders.

    The Address object describes a street address in North America (USA or
    Canada, for now). Callers can use the Address object's methods to find
    the closest or nearby stores from the API.

    Attributes:
        street (str): Street address
        city (str): North American city
        region (str): North American region (state, province, territory)
        zip (str): North American ZIP or postal code
        urls (Urls): Country-specific URLs
        country (str): Country
    """

    def __init__(self, street, city, region='', zip='', country=COUNTRY_USA):
        self.street = str(street).strip()
        self.city = str(city).strip()
        self.region = str(region).strip()
        self.zip = str(zip).strip()
        self.country = validate_country(country)
        self.urls = Urls(self.country)

    @classmethod
    def from_string(cls, address, country=COUNTRY_USA):
        """Build an Address from a single comma-separated string.

        The last field is treated as the ZIP or postal code when it looks like
        one; of what is left, the last two fields are the city and region and
        everything before them is the street. That keeps multi-part streets
        intact::

            >>> Address.from_string('123 Main St, Apt 4, Springfield, IL, 62704')
            123 Main St, Apt 4, Springfield, IL, 62704

        Earlier versions split on commas straight into the constructor, so an
        address with a unit number shifted every field along by one and the ZIP
        was silently parsed as the country.

        Raises:
            InvalidAddressError: If ``address`` has no usable fields.
        """
        if isinstance(address, cls):
            return address

        parts = [part.strip() for part in str(address).split(',')]
        parts = [part for part in parts if part]
        if not parts:
            raise InvalidAddressError('address is empty')

        zip_code = parts.pop() if looks_like_postal_code(parts[-1]) else ''

        street, city, region = '', '', ''
        if len(parts) >= 3:
            street, city, region = ', '.join(parts[:-2]), parts[-2], parts[-1]
        elif len(parts) == 2:
            street, city = parts
        elif len(parts) == 1:
            street = parts[0]

        return cls(street, city, region, zip_code, country)

    def __repr__(self):
        return ", ".join(
            part for part in (self.street, self.city, self.region, self.zip) if part
        )

    @property
    def data(self):
        return {'Street': self.street, 'City': self.city,
                'Region': self.region, 'PostalCode': self.zip}

    @property
    def line1(self):
        return '{Street}'.format(**self.data)

    @property
    def line2(self):
        return '{City}, {Region}, {PostalCode}'.format(**self.data)

    def nearby_stores(self, service='Delivery'):
        """Query the API to find nearby stores.

        nearby_stores will filter the information we receive from the API
        to exclude stores that are not currently online (!['IsOnlineNow']),
        and stores that are not currently in service (!['ServiceIsOpen']).
        """
        data = request_json(self.urls.find_url(), line1=self.line1, line2=self.line2, type=service)
        return [Store(x, self.country) for x in data.get('Stores', [])
                if x.get('IsOnlineNow') and x.get('ServiceIsOpen', {}).get(service)]

    def closest_store(self, service='Delivery'):
        """Return the nearest store that is open for ``service``.

        Raises:
            StoreNotFoundError: If no nearby store is currently open.
        """
        stores = self.nearby_stores(service=service)
        if not stores:
            raise StoreNotFoundError('No local stores are currently open')
        return stores[0]
