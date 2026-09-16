"""The README's quick start, start to finish, against mocked HTTP.

If this file needs changing, the README almost certainly does too.
"""
from mock import patch

from pizzapy import Customer, Order, StoreLocator
from pizzapy.payment import CreditCard

PRICED = {'Status': 0, 'Order': {'Amounts': {'Customer': 16.11}}}
PLACED = {'Status': 1, 'Order': {'OrderID': '4336-1234'}}


def test_the_readme_quick_start(stores_data, menu_data):
    customer = Customer(
        'Barack', 'Obama', 'barack@whitehouse.gov', '2024561111',
        '700 Pennsylvania Avenue NW, Washington, DC, 20408',
    )

    with patch('pizzapy.address.request_json', return_value=stores_data):
        my_local_dominos = StoreLocator.find_closest_store_to_customer(customer)
    assert my_local_dominos.id == '4336'

    with patch('pizzapy.store.request_json', return_value=menu_data):
        menu = my_local_dominos.get_menu()

    cokes = menu.search(Name='Coke')
    assert '20BCOKE' in [item['Code'] for item in cokes]

    order = Order.begin_customer_order(customer, my_local_dominos, menu=menu)
    order.add_item('P12IPAZA')   # a 12-inch pan pizza
    order.add_item('MARINARA')   # with an extra marinara cup
    order.add_item('20BCOKE')    # and a 20oz bottle of coke
    order.remove_item('20BCOKE')
    assert [p['Code'] for p in order.data['Products']] == ['P12IPAZA', 'MARINARA']

    # The exact card from the README, so the two cannot drift apart.
    card = CreditCard('4100 1234 2234 3237', '0130', '777', '90210')
    assert card.validate() is True

    with patch('pizzapy.order.post_json', side_effect=[PRICED, PLACED]) as post:
        receipt = my_local_dominos.place_order(order, card)

    assert receipt == PLACED
    sent = post.call_args[0][1]['Order']
    assert sent['StoreID'] == '4336'
    assert sent['Payments'][0]['CardType'] == 'VISA'
    assert sent['Address']['PostalCode'] == '20408'
    assert sent['SourceOrganizationURI'] == 'order.dominos.com'


def test_the_quick_start_works_for_canada(stores_data, menu_data):
    """The same flow, in Canada, reaching the Canadian endpoints throughout."""
    from pizzapy.urls import COUNTRY_CANADA

    customer = Customer(
        'Barack', 'Obama', 'b@wh.gov', '2024561111',
        '1 Yonge St, Toronto, ON, M5E 1E5', country=COUNTRY_CANADA,
    )

    with patch('pizzapy.address.request_json', return_value=stores_data) as locator:
        store = StoreLocator.find_closest_store_to_customer(customer)
    assert '.ca/' in locator.call_args[0][0]
    assert store.country == COUNTRY_CANADA

    with patch('pizzapy.store.request_json', return_value=menu_data) as menu_call:
        menu = store.get_menu()
    assert '.ca/' in menu_call.call_args[0][0]

    order = Order.begin_customer_order(customer, store, menu=menu)
    order.add_item('P12IPAZA')

    with patch('pizzapy.order.post_json', side_effect=[PRICED, PLACED]) as post:
        order.place(CreditCard('4242424242424242', '0130', '777', 'M5E 1E5'))

    urls = [call[0][0] for call in post.call_args_list]
    assert all('order.dominos.ca' in url for url in urls), urls
    assert post.call_args[1]['headers']['Referer'] == 'https://order.dominos.ca/en/pages/order/'
    assert post.call_args[0][1]['Order']['SourceOrganizationURI'] == 'order.dominos.ca'
