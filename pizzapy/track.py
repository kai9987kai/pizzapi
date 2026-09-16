from .exceptions import PizzaPyError
from .urls import Urls, COUNTRY_USA
from .utils import request_xml, request_json


class TrackingError(PizzaPyError):
    """The tracker had nothing to say about that phone number or order."""


def track_by_phone(phone, country=COUNTRY_USA):
    """Look up the most recent orders placed from a phone number.

    Returns whatever the tracker knows about the order: where it is in the
    make line, which store has it, and when it was placed.

    Raises:
        TrackingError: If the tracker has no orders for that number.
    """
    phone = str(phone).strip()
    data = request_xml(
        Urls(country).track_by_phone(),
        phone=phone
    )

    try:
        body = data['soap:Envelope']['soap:Body']
        return body['GetTrackerDataResponse']['OrderStatuses']['OrderStatus']
    except (KeyError, TypeError):
        raise TrackingError(
            'no orders found for phone number {!r}'.format(phone)
        )


def track_by_order(store_id, order_key, country=COUNTRY_USA):
    """Look up one order by the store it was placed at and its order key."""
    return request_json(
        Urls(country).track_by_order(),
        store_id=store_id,
        order_key=order_key
    )
