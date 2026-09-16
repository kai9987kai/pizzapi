import pytest

from pizzapy.address import Address
from pizzapy.customer import Customer
from pizzapy.exceptions import InvalidAddressError
from pizzapy.urls import COUNTRY_CANADA, COUNTRY_USA


def address_of(string, **kwargs):
    return Customer('Barack', 'Obama', 'b@wh.gov', '2024561111', string, **kwargs).address


def test_the_readme_address_still_parses():
    address = address_of('700 Pennsylvania Avenue NW, Washington, DC, 20408')
    assert address.street == '700 Pennsylvania Avenue NW'
    assert address.city == 'Washington'
    assert address.region == 'DC'
    assert address.zip == '20408'
    assert address.country == COUNTRY_USA


def test_an_address_with_a_unit_number_keeps_its_fields_aligned():
    """A fifth comma used to shift every field along by one.

    The ZIP landed in ``country``, which then blew up on the next API call.
    """
    address = address_of('123 Main St, Apt 4, Springfield, IL, 62704')
    assert address.street == '123 Main St, Apt 4'
    assert address.city == 'Springfield'
    assert address.region == 'IL'
    assert address.zip == '62704'
    assert address.country == COUNTRY_USA


@pytest.mark.parametrize('string,expected', [
    ('123 Main St, Springfield, IL, 62704', ('123 Main St', 'Springfield', 'IL', '62704')),
    ('123 Main St, Springfield, IL', ('123 Main St', 'Springfield', 'IL', '')),
    ('123 Main St, Springfield', ('123 Main St', 'Springfield', '', '')),
    ('123 Main St', ('123 Main St', '', '', '')),
    ('20408', ('', '', '', '20408')),
    ('  123 Main St ,  Springfield , IL , 62704  ', ('123 Main St', 'Springfield', 'IL', '62704')),
])
def test_addresses_with_fewer_fields(string, expected):
    """Short addresses used to raise TypeError from the constructor."""
    address = address_of(string)
    assert (address.street, address.city, address.region, address.zip) == expected


def test_canadian_postal_code_is_recognised():
    address = Address.from_string('1 Yonge St, Toronto, ON, M5E 1E5', COUNTRY_CANADA)
    assert address.zip == 'M5E 1E5'
    assert address.region == 'ON'
    assert address.country == COUNTRY_CANADA
    assert address.urls.country == COUNTRY_CANADA


def test_country_reaches_the_address():
    assert address_of('1 Yonge St, Toronto, ON', country=COUNTRY_CANADA).country == COUNTRY_CANADA


def test_an_address_object_is_accepted_as_is():
    address = Address('700 Pennsylvania Avenue NW', 'Washington', 'DC', '20408')
    assert Customer('Barack', 'Obama', address=address).address is address


def test_address_is_optional():
    assert Customer('Barack', 'Obama').address is None


def test_empty_address_is_rejected_clearly():
    with pytest.raises(InvalidAddressError):
        address_of(' , , ')


def test_fields_are_stripped_and_stringified():
    customer = Customer(' Barack ', ' Obama ', ' b@wh.gov ', 2024561111, '20408')
    assert customer.first_name == 'Barack'
    assert customer.last_name == 'Obama'
    assert customer.email == 'b@wh.gov'
    assert customer.phone == '2024561111'
    assert customer.full_name == 'Barack Obama'


def test_repr_mentions_the_customer(customer):
    assert 'Barack' in repr(customer)
    assert 'Washington' in repr(customer)
