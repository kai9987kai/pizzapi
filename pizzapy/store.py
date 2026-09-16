from .menu import Menu
from .urls import Urls, COUNTRY_USA, validate_country
from .utils import request_json


class Store(object):
    """The interface to the Store API

    You can use this to find store information about stores near an
    address, or to find the closest store to an address.

    Attributes:
        id (str): The store's ID, as the API knows it
        country (str): The country the store is in
        urls (Urls): Country-specific URLs
        data (dict): Whatever the store locator told us about this store
    """

    def __init__(self, data=None, country=COUNTRY_USA):
        self.data = {} if data is None else data
        self.id = str(self.data.get('StoreID', -1))
        self.country = validate_country(country)
        self.urls = Urls(self.country)

    def __repr__(self):
        return "Store #{}\nAddress: {}\n\nOpen Now: {}".format(
            self.id,
            self.data.get('AddressDescription', 'unknown'),
            'Yes' if self.data.get('IsOpen', False) else 'No',
        )

    @property
    def address_description(self):
        """The store's address, as the API formatted it."""
        return self.data.get('AddressDescription', '')

    @property
    def phone(self):
        """The store's phone number."""
        return self.data.get('Phone', '')

    @property
    def is_open(self):
        """Whether the store was open when the locator answered."""
        return bool(self.data.get('IsOpen', False))

    def offers(self, service='Delivery'):
        """Whether the store was serving ``service`` when the locator answered."""
        return bool(self.data.get('ServiceIsOpen', {}).get(service, False))

    def get_details(self):
        """Fetch the store's full profile from the API."""
        details = request_json(self.urls.info_url(), store_id=self.id)
        return details

    def place_order(self, order, card):
        """Place ``order`` at this store, paying with ``card``."""
        return order.place(card=card)

    def get_menu(self, lang='en'):
        """Fetch this store's menu."""
        response = request_json(self.urls.menu_url(), store_id=self.id, lang=lang)
        return Menu(response, self.country)

    def get_coupon(self, code, lang='en'):
        """Fetch the full details of one of this store's coupons."""
        return request_json(
            self.urls.coupon_url(), store_id=self.id, couponid=code, lang=lang
        )


class StoreLocator(object):
    """Find stores that serve a given address or customer.

    Every method here is a thin convenience wrapper over the equivalent
    :class:`~pizzapy.address.Address` method, so the filtering rules live in
    exactly one place.
    """

    def __repr__(self):
        return 'I locate stores and nothing else'

    @staticmethod
    def nearby_stores(address, service='Delivery'):
        """Query the API to find stores near ``address``.

        Only stores that are online and currently serving ``service`` are
        returned.
        """
        return address.nearby_stores(service=service)

    @staticmethod
    def find_closest_store_to_address(address, service='Delivery'):
        """Return the nearest store to ``address`` that is open for ``service``.

        Raises:
            StoreNotFoundError: If no nearby store is currently open.
        """
        return address.closest_store(service=service)

    @staticmethod
    def find_closest_store_to_customer(customer, service='Delivery'):
        """Return the nearest store to ``customer`` that is open for ``service``.

        Raises:
            StoreNotFoundError: If no nearby store is currently open.
        """
        return customer.address.closest_store(service=service)
