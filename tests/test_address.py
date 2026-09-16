import pytest
from hamcrest import *
from mock import patch
from pytest import mark

from pizzapy.address import Address
from pizzapy.exceptions import StoreNotFoundError
from pizzapy.urls import Urls, COUNTRY_CANADA, COUNTRY_USA


address_params = mark.parametrize(
    argnames=('street', 'city', 'region', 'zip'),
    argvalues=[
        ('700 Pennsylvania Avenue NW', 'Washington', 'DC', '20408'),
        ('700 Pennsylvania Avenue NW ', ' Washington ', ' DC ', ' 20408 '),
        ('700 Pennsylvania Avenue NW', 'Washington', 'DC', 20408)
    ]
)


@pytest.fixture
def locator(stores_data):
    """Patch the store locator call, checking what it was asked for."""
    def mocked_request_json(url, **kwargs):
        assert_that(url, equal_to(Urls(COUNTRY_USA).find_url()))
        assert_that(kwargs, has_entries(
            line1='700 Pennsylvania Avenue NW',
            line2='Washington, DC, 20408',
            type='Delivery'
        ))
        return stores_data

    with patch('pizzapy.address.request_json', side_effect=mocked_request_json) as mocked:
        yield mocked


@address_params
def test_address_init(street, city, region, zip):
    address = Address(street, city, region, zip)
    assert_that(address, has_properties(
        street='700 Pennsylvania Avenue NW',
        city='Washington',
        region='DC',
        zip='20408',
        line1='700 Pennsylvania Avenue NW',
        line2='Washington, DC, 20408',
        data=has_entries(
            Street='700 Pennsylvania Avenue NW',
            City='Washington',
            Region='DC',
            PostalCode='20408'
        )
    ))


@address_params
def test_address_closest_store(locator, street, city, region, zip, stores_data):
    address = Address(street, city, region, zip)
    store = address.closest_store()
    assert_that(store, has_properties(
        id='4336',
        country=COUNTRY_USA,
        data=has_entries(
            AddressDescription='1300 L St Nw\nWashington, DC 20005',
            Phone='202-639-8700',
            IsOnlineNow=True,
            IsOpen=True,
            ServiceIsOpen=has_entries(Carryout=True, Delivery=True),
            StoreID='4336',
        )
    ))
    assert_that(store.data, equal_to(stores_data['Stores'][0]))


@address_params
def test_address_nearby_stores(locator, street, city, region, zip, stores_data):
    stores = Address(street, city, region, zip).nearby_stores()
    assert_that(stores, has_length(12))
    assert_that([x.data for x in stores], equal_to(stores_data['Stores']))


def test_repr_skips_empty_fields():
    assert repr(Address('123 Main St', 'Springfield')) == '123 Main St, Springfield'
    assert repr(Address('123 Main St', 'Springfield', 'IL', '62704')) == \
        '123 Main St, Springfield, IL, 62704'


def test_country_selects_the_urls():
    assert_that(Address('1 Yonge St', 'Toronto', 'ON', 'M5E 1E5', COUNTRY_CANADA).urls,
                has_property('country', COUNTRY_CANADA))


def test_an_unsupported_country_is_rejected():
    """A fifth comma in a customer address used to land the ZIP here."""
    with pytest.raises(ValueError):
        Address('123 Main St', 'Springfield', 'IL', '62704', '62704')


def test_no_open_store_raises_store_not_found():
    with patch('pizzapy.address.request_json', return_value={'Stores': []}):
        with pytest.raises(StoreNotFoundError):
            Address('123 Main St', 'Springfield', 'IL', '62704').closest_store()


def test_a_missing_stores_key_is_handled():
    with patch('pizzapy.address.request_json', return_value={'Status': -1}):
        assert Address('123 Main St', 'Springfield').nearby_stores() == []
