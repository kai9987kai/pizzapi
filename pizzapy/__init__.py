"""A Python wrapper for the Domino's Pizza API."""
from .address import Address
from .coupon import Coupon
from .customer import Customer
from .exceptions import (
    InvalidAddressError,
    InvalidCountryError,
    ItemNotFoundError,
    OrderError,
    PizzaPyError,
    StoreNotFoundError,
)
from .menu import Menu, MenuCategory, MenuItem
from .order import Order
from .payment import CreditCard
from .store import Store, StoreLocator
from .track import TrackingError, track_by_order, track_by_phone
from .urls import COUNTRIES, COUNTRY_CANADA, COUNTRY_USA, Urls
from .utils import get_session, request_json, request_xml, set_session

__version__ = '0.1.0'

__all__ = [
    'Address',
    'COUNTRIES',
    'COUNTRY_CANADA',
    'COUNTRY_USA',
    'Coupon',
    'CreditCard',
    'Customer',
    'InvalidAddressError',
    'InvalidCountryError',
    'ItemNotFoundError',
    'Menu',
    'MenuCategory',
    'MenuItem',
    'Order',
    'OrderError',
    'PizzaPyError',
    'Store',
    'StoreLocator',
    'StoreNotFoundError',
    'TrackingError',
    'Urls',
    '__version__',
    'get_session',
    'request_json',
    'request_xml',
    'set_session',
    'track_by_order',
    'track_by_phone',
]
