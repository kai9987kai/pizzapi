import pytest
from mock import patch

from pizzapy.exceptions import StoreNotFoundError
from pizzapy.store import Store, StoreLocator
from pizzapy.urls import COUNTRY_CANADA


def test_repr_survives_a_store_with_no_data():
    """Store() with no data used to raise KeyError from __repr__."""
    assert 'Store #-1' in repr(Store())


def test_repr_shows_what_the_locator_said(store):
    text = repr(store)
    assert 'Store #4336' in text
    assert '1300 L St Nw' in text
    assert 'Open Now: Yes' in text


def test_convenience_properties(store):
    assert store.id == '4336'
    assert store.phone == '202-639-8700'
    assert store.is_open is True
    assert store.offers('Delivery') is True
    assert store.offers('Nonsense') is False
    assert '1300 L St Nw' in store.address_description


def test_properties_are_safe_on_an_empty_store():
    empty = Store()
    assert empty.phone == ''
    assert empty.address_description == ''
    assert empty.is_open is False
    assert empty.offers('Delivery') is False


def test_country_reaches_the_urls():
    assert Store({}, COUNTRY_CANADA).urls.country == COUNTRY_CANADA
    assert '.ca/' in Store({}, COUNTRY_CANADA).urls.menu_url()


def test_default_data_is_not_shared_between_stores():
    """data={} as a default argument would be shared by every Store."""
    first = Store()
    first.data['sneaky'] = True
    assert Store().data == {}


@patch('pizzapy.store.request_json')
def test_get_menu_passes_store_and_country(request_json, menu_data):
    request_json.return_value = menu_data
    menu = Store({'StoreID': '4336'}, COUNTRY_CANADA).get_menu()
    assert request_json.call_args[1]['store_id'] == '4336'
    assert menu.country == COUNTRY_CANADA


@patch('pizzapy.store.request_json')
def test_get_coupon_reaches_the_coupon_endpoint(request_json):
    """The coupon URL was in the URL table but nothing could reach it."""
    request_json.return_value = {'Code': '9193'}
    Store({'StoreID': '4336'}).get_coupon('9193')
    url, kwargs = request_json.call_args[0][0], request_json.call_args[1]
    assert '/coupon/' in url
    assert kwargs == {'store_id': '4336', 'couponid': '9193', 'lang': 'en'}


def test_locator_delegates_to_the_address(customer, stores_data):
    """The locator and Address used to hold duplicate copies of the filtering."""
    with patch('pizzapy.address.request_json', return_value=stores_data):
        from_locator = StoreLocator.nearby_stores(customer.address)
        from_address = customer.address.nearby_stores()
    assert [s.id for s in from_locator] == [s.id for s in from_address]


def test_locator_finds_the_closest_store_to_a_customer(customer, stores_data):
    with patch('pizzapy.address.request_json', return_value=stores_data):
        assert StoreLocator.find_closest_store_to_customer(customer).id == '4336'
        assert StoreLocator.find_closest_store_to_address(customer.address).id == '4336'


def test_no_open_stores_raises_a_named_error(customer):
    with patch('pizzapy.address.request_json', return_value={'Stores': []}):
        with pytest.raises(StoreNotFoundError):
            StoreLocator.find_closest_store_to_customer(customer)


def test_closed_stores_are_filtered_out(customer, stores_data):
    closed = {'Stores': [dict(s, IsOnlineNow=False) for s in stores_data['Stores']]}
    with patch('pizzapy.address.request_json', return_value=closed):
        assert customer.address.nearby_stores() == []


def test_a_store_missing_service_info_is_skipped(customer):
    """A store without ServiceIsOpen used to raise KeyError mid-search."""
    with patch('pizzapy.address.request_json',
               return_value={'Stores': [{'StoreID': '1', 'IsOnlineNow': True}]}):
        assert customer.address.nearby_stores() == []
