"""Exceptions raised by pizzapy.

Every exception raised deliberately by this library derives from
:class:`PizzaPyError`, so callers can catch the whole family with a single
``except PizzaPyError``.

Where an older version of pizzapy raised a builtin, the replacement also
derives from that builtin, so existing ``except KeyError`` / ``except
ValueError`` handlers keep working.
"""


class PizzaPyError(Exception):
    """Base class for every error raised by pizzapy."""


class StoreNotFoundError(PizzaPyError):
    """No store matched the search, or no matching store is currently open."""


class ItemNotFoundError(PizzaPyError, KeyError):
    """A product code is not on the menu, or is not in the order.

    Derives from :class:`KeyError` because looking a code up on the menu used
    to raise one.
    """

    def __str__(self):
        # KeyError.__str__ reprs its argument ("'no such item'"), which turns
        # readable messages into quoted noise. Use the plain Exception form.
        return Exception.__str__(self)


class InvalidCountryError(PizzaPyError, ValueError):
    """A country code other than the supported ones was supplied."""


class InvalidAddressError(PizzaPyError, ValueError):
    """An address could not be understood."""


class OrderError(PizzaPyError):
    """The API rejected an order, or the order is not ready to be sent.

    Attributes:
        response (dict): The decoded API response, when there was one.
    """

    def __init__(self, message, response=None):
        super(OrderError, self).__init__(message)
        self.response = response
