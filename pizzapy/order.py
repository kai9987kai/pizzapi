import copy

from .exceptions import InvalidAddressError, ItemNotFoundError, OrderError
from .menu import Menu
from .urls import Urls, COUNTRY_USA
from .utils import post_json


class Order(object):
    """Core interface to the payments API.

    The Order wraps up all the logic for actually placing the order, after
    we've determined what we want from the Menu.

    Attributes:
        store (Store): Where the order is going
        customer (Customer): Who is ordering
        menu (Menu): The store's menu, used to look up item codes
        data (dict): The order payload, as the API wants it
    """

    def __init__(self, store, customer, country=None, menu=None):
        """Start an order at ``store`` for ``customer``.

        Args:
            country: Defaults to the store's own country, so a Canadian store
                is no longer ordered from through the US endpoints.
            menu: An already-fetched :class:`~pizzapy.menu.Menu`. Pass the one
                from ``store.get_menu()`` to skip a second download.
        """
        if getattr(customer, 'address', None) is None:
            raise InvalidAddressError(
                'cannot start an order: {} has no address'.format(
                    getattr(customer, 'full_name', None) or 'this customer'
                )
            )
        if country is None:
            country = getattr(store, 'country', COUNTRY_USA)
        self.store = store
        self.menu = menu if menu is not None else Menu.from_store(
            store_id=store.id, country=country
        )
        self.customer = customer
        self.address = customer.address
        self.country = country
        self.urls = Urls(country)
        self.data = {
            'Address': {'Street': self.address.street,
                        'City': self.address.city,
                        'Region': self.address.region,
                        'PostalCode': self.address.zip,
                        'Type': 'House'},
            'Coupons': [], 'CustomerID': '', 'Extension': '',
            'OrderChannel': 'OLO', 'OrderID': '', 'NoCombine': True,
            'OrderMethod': 'Web', 'OrderTaker': None, 'Payments': [],
            'Products': [], 'Market': '', 'Currency': '',
            'ServiceMethod': 'Delivery', 'Tags': {}, 'Version': '1.0',
            'SourceOrganizationURI': self.urls.order_host, 'LanguageCode': 'en',
            'Partners': {}, 'NewUser': True, 'metaData': {}, 'Amounts': {},
            'BusinessDate': '', 'EstimatedWaitMinutes': '',
            'PriceOrderTime': '', 'AmountsBreakdown': {}
            }

    @staticmethod
    def begin_customer_order(customer, store, country=None, menu=None):
        return Order(store, customer, country=country, menu=menu)

    def __repr__(self):
        return "An order for {} with {} items in it\n".format(
            self.customer.first_name,
            len(self.data['Products']) if self.data['Products'] else 'no',
        )

    @staticmethod
    def _build_options(options):
        """Normalise ``options`` into the ``{code: {'1/1': qty}}`` form.

        Accepts a list of topping codes (``['P', 'X']``) or an already-built
        dict, which is passed through untouched.
        """
        if isinstance(options, dict):
            return copy.deepcopy(options)
        return {str(code): {'1/1': '1'} for code in options}

    def _prepare(self, code, qty, options, lookup=None):
        """Look ``code`` up on the menu and return an orderable copy of it.

        The copy matters: the menu holds one dict per code, so adding an item
        used to write the quantity straight into the menu and adding the same
        item twice appended the *same* dict twice.
        """
        lookup = lookup or self.menu.get_variant
        item = copy.deepcopy(lookup(code))
        item.update(ID=self._next_item_id(), isNew=True, Qty=qty, AutoRemove=False)
        if options:
            item['Options'] = self._build_options(options)
        return item

    def _next_item_id(self):
        """Order lines need distinct IDs; they were all hardcoded to 1."""
        used = [x.get('ID', 0) for x in self.data['Products'] + self.data['Coupons']]
        return max(used) + 1 if used else 1

    def add_item(self, code, qty=1, options=None):
        """Add ``qty`` of the menu item ``code`` to the order.

        Args:
            options: Toppings to add, either a list of topping codes or a dict
                in the API's own ``{code: {portion: qty}}`` form. Left alone
                when omitted.

        Raises:
            ItemNotFoundError: If ``code`` is not on the store's menu.
        """
        item = self._prepare(code, qty, options)
        self.data['Products'].append(item)
        return item

    def remove_item(self, code):
        """Remove the first item with ``code`` from the order.

        Raises:
            ItemNotFoundError: If no item in the order has that code.
        """
        return self._remove_from('Products', code)

    def add_coupon(self, code, qty=1):
        """Add the coupon ``code`` to the order.

        Raises:
            ItemNotFoundError: If ``code`` is not a coupon on the store's menu.
        """
        item = self._prepare(code, qty, None, lookup=self.menu.get_coupon)
        self.data['Coupons'].append(item)
        return item

    def remove_coupon(self, code):
        """Remove the first coupon with ``code`` from the order.

        Raises:
            ItemNotFoundError: If no coupon in the order has that code.
        """
        return self._remove_from('Coupons', code)

    def _remove_from(self, key, code):
        codes = [x['Code'] for x in self.data[key]]
        if code not in codes:
            raise ItemNotFoundError(
                'no item with code {!r} in this order'.format(code)
            )
        return self.data[key].pop(codes.index(code))

    def _send(self, url, merge):
        self.data.update(
            StoreID=self.store.id,
            Email=self.customer.email,
            FirstName=self.customer.first_name,
            LastName=self.customer.last_name,
            Phone=self.customer.phone,
        )

        for key in ('Products', 'StoreID', 'Address'):
            if key not in self.data or not self.data[key]:
                raise OrderError('order has invalid value for key "%s"' % key)

        headers = {
            'Referer': self.urls.referer,
            'Content-Type': 'application/json'
        }

        json_data = post_json(url, {'Order': self.data}, headers=headers)

        if merge:
            for key, value in json_data['Order'].items():
                if value or not isinstance(value, list):
                    self.data[key] = value
        return json_data

    @staticmethod
    def _status_message(response):
        """Pull the API's own explanation out of a rejected response.

        Runs while building an exception, so it never raises one of its own:
        anything unexpected in the response just yields an empty string.
        """
        if not isinstance(response, dict):
            return ''
        order = response.get('Order')
        items = (order if isinstance(order, dict) else response).get('StatusItems', [])
        if not isinstance(items, list):
            return ''
        reasons = [i.get('Code', '') for i in items if isinstance(i, dict)]
        return ', '.join(r for r in reasons if r)

    def validate(self):
        """Ask the API whether this order is orderable. Returns a bool."""
        response = self._send(self.urls.validate_url(), True)
        return response['Status'] != -1

    def _fetch_price(self):
        """Ask the API to price the order, merging its answer into self.data.

        Raises:
            OrderError: If the API could not price the order.
        """
        response = self._send(self.urls.price_url(), True)
        if response['Status'] == -1:
            raise OrderError(
                'get price failed: {}'.format(self._status_message(response) or response),
                response,
            )
        return response

    def price(self):
        """Price the order and return the amounts the API worked out.

        Raises:
            OrderError: If the API could not price the order.
        """
        self._fetch_price()
        return self.data.get('Amounts', {})

    def place(self, card=False):
        """Pay for and place the order.

        Raises:
            OrderError: If the API rejects the order. Previously a rejected
                order came back as an ordinary response and looked placed.
        """
        self.pay_with(card)
        response = self._send(self.urls.place_url(), False)
        if response.get('Status') == -1:
            raise OrderError(
                'order failed: {}'.format(self._status_message(response) or response),
                response,
            )
        return response

    def pay_with(self, card=False):
        """Price the order and attach payment. Use this instead of place when testing."""
        # get the price to check that everything worked okay
        response = self._fetch_price()

        if card is False:
            self.data['Payments'] = [
                {
                    'Type': 'Cash',
                }
            ]
        else:
            self.data['Payments'] = [
                {
                    'Type': 'CreditCard',
                    'Expiration': card.expiration,
                    'Amount': self.data['Amounts'].get('Customer', 0),
                    'CardType': card.card_type,
                    'Number': int(card.number),
                    # Sent as text: int() drops a leading zero from a CVV and
                    # cannot hold a ZIP+4 or a Canadian postal code at all.
                    'SecurityCode': card.cvv,
                    'PostalCode': card.zip,
                }
            ]

        return response
