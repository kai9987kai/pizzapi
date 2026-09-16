import datetime

import pytest

from pizzapy.payment import CreditCard

# Standard test numbers: every one of these passes the Luhn checksum.
VISA = '4242424242424242'
MASTERCARD = '5500005555555559'
MASTERCARD_2_SERIES = '2223003122003222'
AMEX = '378282246310005'
DISCOVER = '6011111111111117'


def card(number=VISA, expiration='0130', cvv='777', zip='90210'):
    return CreditCard(number, expiration, cvv, zip)


def test_validate_returns_a_bool_instead_of_raising():
    """validate() used to raise TypeError for every card, valid or not.

    It combined a string with a regex match object using ``&=``.
    """
    result = card().validate()
    assert result is True
    assert card(number='1234').validate() is False


@pytest.mark.parametrize('number,expected', [
    (VISA, 'VISA'),
    (MASTERCARD, 'MASTERCARD'),
    (MASTERCARD_2_SERIES, 'MASTERCARD'),
    (AMEX, 'AMEX'),
    (DISCOVER, 'DISCOVER'),
    ('not a card', ''),
])
def test_find_type(number, expected):
    assert CreditCard(number).card_type == expected


def test_two_series_mastercard_is_recognised():
    """The 2221-2720 range has been live since 2016 and was not matched."""
    assert CreditCard(MASTERCARD_2_SERIES).card_type == 'MASTERCARD'


def test_number_is_normalised():
    assert CreditCard('4242 4242 4242 4242').number == VISA
    assert CreditCard('4242-4242-4242-4242').card_type == 'VISA'


def test_expiration_is_normalised():
    assert CreditCard(VISA, '01/30').expiration == '0130'
    assert card(expiration='01/30').validate() is True


@pytest.mark.parametrize('number,valid', [
    (VISA, True),
    ('4100123422343234', False),  # right shape, wrong checksum
    ('', False),
    ('abcd', False),
])
def test_luhn_valid(number, valid):
    assert CreditCard(number).luhn_valid() is valid


@pytest.mark.parametrize('kwargs', [
    {'number': '4100123422343234'},   # fails the Luhn checksum
    {'number': ''},
    {'expiration': '1330'},           # month 13
    {'expiration': ''},
    {'cvv': '77'},
    {'cvv': 'abc'},
    {'zip': '902'},
    {'zip': ''},
])
def test_validate_rejects_bad_fields(kwargs):
    assert card(**kwargs).validate() is False


@pytest.mark.parametrize('zip', ['90210', '90210-1234', 'M5E 1E5', 'M5E1E5'])
def test_validate_accepts_us_and_canadian_postal_codes(zip):
    assert card(zip=zip).validate() is True


def test_cvv_keeps_a_leading_zero():
    """int() on the security code would turn '012' into 12."""
    assert card(cvv='012').cvv == '012'
    assert card(cvv='012').validate() is True


def test_is_expired():
    today = datetime.date(2026, 9, 16)
    assert card(expiration='0120').is_expired(today) is True
    assert card(expiration='0130').is_expired(today) is False
    # A card is good through the last day of its expiry month.
    assert card(expiration='0926').is_expired(today) is False
    assert card(expiration='0826').is_expired(today) is True


def test_is_expired_is_false_for_an_unparseable_date():
    assert card(expiration='nope').is_expired(datetime.date(2026, 9, 16)) is False


def test_repr_shows_only_the_last_four():
    assert repr(card()) == 'Credit Card with last four #4242'
    assert VISA[:12] not in repr(card())
