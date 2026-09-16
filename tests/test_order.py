import pytest
from mock import patch

from pizzapy.exceptions import ItemNotFoundError, OrderError
from pizzapy.menu import Menu
from pizzapy.order import Order
from pizzapy.payment import CreditCard
from pizzapy.store import Store
from pizzapy.urls import COUNTRY_CANADA

PAN_PIZZA = 'P12IPAZA'
COKE = '20BCOKE'
COUPON = '9174'  # a real coupon code from the fixture

PRICED = {'Status': 0, 'Order': {'Amounts': {'Customer': 16.11}, 'OrderID': 'abc'}}
PLACED = {'Status': 1, 'Order': {'OrderID': 'abc'}}
REJECTED = {'Status': -1, 'Order': {'StatusItems': [{'Code': 'MinimumOrderAmount'}]}}


@pytest.fixture
def card():
    return CreditCard('4242424242424242', '0130', '777', '90210')


def test_adding_an_item_does_not_touch_the_menu(order, menu):
    """add_item used to write Qty straight into the shared menu data."""
    before = dict(menu.variants[PAN_PIZZA])
    order.add_item(PAN_PIZZA, qty=3)
    assert menu.variants[PAN_PIZZA] == before
    assert 'Qty' not in menu.variants[PAN_PIZZA]


def test_the_same_item_twice_gives_two_independent_lines(order):
    """Both lines used to be the *same* dict, so one Qty overwrote the other."""
    first = order.add_item(PAN_PIZZA, qty=1)
    second = order.add_item(PAN_PIZZA, qty=5)
    assert first is not second
    assert first['Qty'] == 1
    assert second['Qty'] == 5
    assert len(order.data['Products']) == 2


def test_order_lines_get_distinct_ids(order):
    """Every line was hardcoded to ID 1."""
    order.add_item(PAN_PIZZA)
    order.add_item(COKE)
    order.add_coupon(COUPON)
    ids = [p['ID'] for p in order.data['Products']] + [c['ID'] for c in order.data['Coupons']]
    assert len(set(ids)) == len(ids)


def test_add_item_sets_the_fields_the_api_wants(order):
    item = order.add_item(PAN_PIZZA, qty=2)
    assert item['Code'] == PAN_PIZZA
    assert item['Qty'] == 2
    assert item['isNew'] is True
    assert item['AutoRemove'] is False
    assert order.data['Products'][0] is item


def test_add_item_rejects_an_unknown_code(order):
    with pytest.raises(ItemNotFoundError) as excinfo:
        order.add_item('NOT_A_CODE')
    assert 'NOT_A_CODE' in str(excinfo.value)
    assert order.data['Products'] == []


def test_options_are_attached_when_given(order):
    """options was accepted and then ignored entirely."""
    item = order.add_item(PAN_PIZZA, options=['P', 'X'])
    assert item['Options'] == {'P': {'1/1': '1'}, 'X': {'1/1': '1'}}


def test_options_accept_the_apis_own_shape(order):
    item = order.add_item(PAN_PIZZA, options={'P': {'1/2': '1.5'}})
    assert item['Options'] == {'P': {'1/2': '1.5'}}


def test_no_options_means_no_options_key(order):
    assert 'Options' not in order.add_item(PAN_PIZZA)


def test_remove_item(order):
    order.add_item(PAN_PIZZA)
    order.add_item(COKE)
    removed = order.remove_item(COKE)
    assert removed['Code'] == COKE
    assert [p['Code'] for p in order.data['Products']] == [PAN_PIZZA]


def test_removing_a_missing_item_says_so(order):
    """This used to raise a bare ValueError from list.index()."""
    order.add_item(PAN_PIZZA)
    with pytest.raises(ItemNotFoundError) as excinfo:
        order.remove_item(COKE)
    assert COKE in str(excinfo.value)


def test_coupons_add_and_remove(order):
    """Coupon codes are not menu variants, so add_coupon always raised."""
    order.add_coupon(COUPON)
    assert [c['Code'] for c in order.data['Coupons']] == [COUPON]
    order.remove_coupon(COUPON)
    assert order.data['Coupons'] == []
    with pytest.raises(ItemNotFoundError):
        order.remove_coupon(COUPON)


def test_add_coupon_does_not_touch_the_menu(order, menu):
    before = dict(menu.coupons_by_code[COUPON])
    order.add_coupon(COUPON, qty=2)
    assert menu.coupons_by_code[COUPON] == before


def test_add_coupon_rejects_an_unknown_code(order):
    with pytest.raises(ItemNotFoundError):
        order.add_coupon('NOT_A_COUPON')


def test_a_supplied_menu_is_reused_instead_of_refetched(store, customer, menu):
    with patch('pizzapy.menu.request_json') as request_json:
        order = Order(store, customer, menu=menu)
    assert order.menu is menu
    request_json.assert_not_called()


def test_country_defaults_to_the_stores_country(customer, menu):
    """A Canadian store used to be ordered from through the US endpoints."""
    canadian_store = Store({'StoreID': '99'}, COUNTRY_CANADA)
    order = Order(canadian_store, customer, menu=menu)
    assert order.country == COUNTRY_CANADA
    assert order.data['SourceOrganizationURI'] == 'order.dominos.ca'
    assert '.ca/' in order.urls.place_url()


def test_us_orders_are_unchanged(order):
    assert order.data['SourceOrganizationURI'] == 'order.dominos.com'


def test_repr_counts_the_items(order):
    assert 'no items' in repr(order)
    order.add_item(PAN_PIZZA)
    assert '1 items' in repr(order)


@patch('pizzapy.order.post_json')
def test_price_sends_the_order_and_returns_the_amounts(post_json, order):
    post_json.return_value = PRICED
    order.add_item(PAN_PIZZA)
    assert order.price() == {'Customer': 16.11}
    url, payload = post_json.call_args[0]
    assert url == order.urls.price_url()
    assert payload['Order']['Products'][0]['Code'] == PAN_PIZZA
    assert payload['Order']['StoreID'] == order.store.id


@patch('pizzapy.order.post_json')
def test_the_referer_header_follows_the_country(post_json, customer, menu):
    post_json.return_value = PRICED
    order = Order(Store({'StoreID': '99'}, COUNTRY_CANADA), customer, menu=menu)
    order.add_item(PAN_PIZZA)
    order.price()
    assert post_json.call_args[1]['headers']['Referer'] == \
        'https://order.dominos.ca/en/pages/order/'


@patch('pizzapy.order.post_json')
def test_price_failure_explains_itself(post_json, order):
    post_json.return_value = REJECTED
    order.add_item(PAN_PIZZA)
    with pytest.raises(OrderError) as excinfo:
        order.price()
    assert 'MinimumOrderAmount' in str(excinfo.value)
    assert excinfo.value.response == REJECTED


@patch('pizzapy.order.post_json')
def test_validate_reports_the_api_verdict(post_json, order):
    order.add_item(PAN_PIZZA)
    post_json.return_value = PRICED
    assert order.validate() is True
    post_json.return_value = REJECTED
    assert order.validate() is False


@patch('pizzapy.order.post_json')
def test_an_empty_order_is_not_sent(post_json, order):
    with pytest.raises(OrderError) as excinfo:
        order.price()
    assert 'Products' in str(excinfo.value)
    post_json.assert_not_called()


@patch('pizzapy.order.post_json')
def test_pay_with_card_builds_the_payment(post_json, order, card):
    post_json.return_value = PRICED
    order.add_item(PAN_PIZZA)
    order.pay_with(card)
    payment = order.data['Payments'][0]
    assert payment['Type'] == 'CreditCard'
    assert payment['CardType'] == 'VISA'
    assert payment['Amount'] == 16.11
    assert payment['Expiration'] == '0130'


@patch('pizzapy.order.post_json')
def test_payment_keeps_leading_zeros_and_long_postal_codes(post_json, order):
    """int() dropped a CVV's leading zero and crashed on a ZIP+4."""
    post_json.return_value = PRICED
    order.add_item(PAN_PIZZA)
    order.pay_with(CreditCard('4242424242424242', '0130', '012', '90210-1234'))
    payment = order.data['Payments'][0]
    assert payment['SecurityCode'] == '012'
    assert payment['PostalCode'] == '90210-1234'


@patch('pizzapy.order.post_json')
def test_pay_with_no_card_is_cash(post_json, order):
    post_json.return_value = PRICED
    order.add_item(PAN_PIZZA)
    order.pay_with()
    assert order.data['Payments'] == [{'Type': 'Cash'}]


@patch('pizzapy.order.post_json')
def test_pay_with_returns_the_price_response(post_json, order, card):
    post_json.return_value = PRICED
    order.add_item(PAN_PIZZA)
    assert order.pay_with(card) == PRICED


@patch('pizzapy.order.post_json')
def test_place_prices_then_places(post_json, order, card):
    post_json.side_effect = [PRICED, PLACED]
    order.add_item(PAN_PIZZA)
    assert order.place(card) == PLACED
    assert [call[0][0] for call in post_json.call_args_list] == \
        [order.urls.price_url(), order.urls.place_url()]


@patch('pizzapy.order.post_json')
def test_a_rejected_order_raises_instead_of_looking_placed(post_json, order, card):
    """place() used to hand back the rejection as if it were a receipt."""
    post_json.side_effect = [PRICED, REJECTED]
    order.add_item(PAN_PIZZA)
    with pytest.raises(OrderError) as excinfo:
        order.place(card)
    assert 'MinimumOrderAmount' in str(excinfo.value)
    assert excinfo.value.response == REJECTED


@patch('pizzapy.order.post_json')
def test_status_message_never_raises_on_an_odd_response(post_json, order, card):
    post_json.side_effect = [PRICED, {'Status': -1, 'Order': 'unexpected'}]
    order.add_item(PAN_PIZZA)
    with pytest.raises(OrderError):
        order.place(card)


def test_begin_customer_order_matches_the_constructor(store, customer, menu):
    order = Order.begin_customer_order(customer, store, menu=menu)
    assert order.store is store
    assert order.customer is customer
    assert order.menu is menu


def test_a_customer_without_an_address_cannot_order(store, menu):
    from pizzapy.customer import Customer
    from pizzapy.exceptions import InvalidAddressError

    with pytest.raises(InvalidAddressError) as excinfo:
        Order(store, Customer('Barack', 'Obama'), menu=menu)
    assert 'Barack Obama' in str(excinfo.value)
