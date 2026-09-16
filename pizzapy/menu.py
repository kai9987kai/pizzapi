from __future__ import print_function

from .exceptions import ItemNotFoundError
from .urls import Urls, COUNTRY_USA, validate_country
from .utils import request_json


class MenuCategory(object):
    """A node in the menu tree, holding products and further categories."""

    def __init__(self, menu_data=None, parent=None):
        menu_data = {} if menu_data is None else menu_data
        self.menu_data = menu_data
        self.subcategories = []
        self.products = []
        self.parent = parent
        self.code = menu_data.get('Code', '')
        self.name = menu_data.get('Name', '')

    def __repr__(self):
        return 'MenuCategory({!r})'.format(self.name)

    def get_category_path(self):
        path = '' if not self.parent else self.parent.get_category_path()
        return path + self.code


class MenuItem(object):
    """One orderable thing on the menu."""

    def __init__(self, data=None):
        data = {} if data is None else data
        self.code = data.get('Code', '')
        self.name = data.get('Name', '')
        self.menu_data = data
        self.categories = []

    def __repr__(self):
        return 'MenuItem({!r}, {!r})'.format(self.code, self.name)


class Menu(object):
    """A store's menu, and the search tools for finding things on it.

    The API hands back one flat table of *variants* (the orderable codes, such
    as ``P12IPAZA``) plus a tree of categories over them. This class keeps both:
    :meth:`search` looks through the flat table, :meth:`display` walks the tree.

    Attributes:
        variants (dict): Every orderable code, mapped to its API data
        menu_by_code (dict): Every product/coupon code, mapped to a MenuItem
        root_categories (dict): The top of each category tree
        country (str): The country whose menu this is
    """

    def __init__(self, data=None, country=COUNTRY_USA):
        data = {} if data is None else data
        self.variants = data.get('Variants', {})
        self.menu_by_code = {}
        self.root_categories = {}
        self.country = validate_country(country)
        # Initialised up front: reading menu.coupons on an empty menu used to
        # raise AttributeError.
        self.products = []
        self.coupons = []
        self.preconfigured = []
        self.coupons_by_code = {}

        if self.variants:
            self.products = self.parse_items(data['Products'])
            self.coupons = self.parse_items(data['Coupons'])
            self.preconfigured = self.parse_items(data['PreconfiguredProducts'])
            self.coupons_by_code = {c.code: c.menu_data for c in self.coupons}
            for key, value in data['Categorization'].items():
                self.root_categories[key] = self.build_categories(value)

    @classmethod
    def from_store(cls, store_id, lang='en', country=COUNTRY_USA):
        """Fetch the menu for ``store_id`` straight from the API."""
        response = request_json(
            Urls(country).menu_url(), store_id=store_id, lang=lang
        )
        return cls(response, country)

    def __repr__(self):
        return 'Menu with {} orderable items'.format(len(self.variants))

    # TODO: Reconfigure structure to show that Codes (not ProductCodes) matter
    def build_categories(self, category_data, parent=None):
        category = MenuCategory(category_data, parent)
        for subcategory in category_data['Categories']:
            new_subcategory = self.build_categories(subcategory, category)
            category.subcategories.append(new_subcategory)
        for product_code in category_data['Products']:
            if product_code not in self.menu_by_code:
                raise ItemNotFoundError(
                    'PRODUCT NOT FOUND: %s %s' % (product_code, category.code)
                )
            product = self.menu_by_code[product_code]
            category.products.append(product)
            product.categories.append(category)
        return category

    def parse_items(self, parent_data):
        items = []
        for code in parent_data.keys():
            obj = MenuItem(parent_data[code])
            self.menu_by_code[obj.code] = obj
            items.append(obj)
        return items

    def get_variant(self, code):
        """Return the API data for the orderable ``code``.

        Raises:
            ItemNotFoundError: If ``code`` is not on this menu.
        """
        try:
            return self.variants[code]
        except KeyError:
            raise ItemNotFoundError(
                'no item with code {!r} on this menu'.format(code)
            )

    def get_coupon(self, code):
        """Return the API data for the coupon ``code``.

        Coupons live in their own part of the menu, not among the orderable
        variants, so looking one up in ``menu.variants`` always failed.

        Raises:
            ItemNotFoundError: If ``code`` is not a coupon on this menu.
        """
        if code in self.coupons_by_code:
            return self.coupons_by_code[code]
        if code in self.variants:
            return self.variants[code]
        raise ItemNotFoundError(
            'no coupon with code {!r} on this menu'.format(code)
        )

    def display(self):
        """Print the whole menu tree, category by category."""
        def print_category(category, depth=1):
            indent = "  " * (depth + 1)
            if len(category.products) + len(category.subcategories) > 0:
                print(indent + category.name)
                for subcategory in category.subcategories:
                    print_category(subcategory, depth + 1)
                for product in category.products:
                    print(indent + "  [%s]" % product.code, product.name)

        for title, key in (('Coupon Menu', 'Coupons'),
                           ('Preconfigured Menu', 'PreconfiguredProducts'),
                           ('Regular Menu', 'Food')):
            category = self.root_categories.get(key)
            if category is None:
                continue
            print("************ {} ************".format(title))
            print_category(category)
            print()

    @staticmethod
    def parse_toppings(variant):
        """Return a variant's default toppings as a ``{code: portion}`` dict."""
        default = variant.get('Tags', {}).get('DefaultToppings', '') or ''
        return dict(x.split('=', 1) for x in default.split(',') if '=' in x)

    @staticmethod
    def _matches_one(value, wanted):
        """True if ``wanted`` is in ``value``, case-insensitively for strings."""
        if isinstance(value, str) and isinstance(wanted, str):
            return wanted.lower() in value.lower()
        if isinstance(value, (list, tuple, dict)):
            return wanted in value
        return value == wanted

    @classmethod
    def _matches(cls, value, wanted):
        """True if ``value`` matches ``wanted``, or any of it when it's a list."""
        if isinstance(wanted, (list, tuple, set, frozenset)):
            return any(cls._matches_one(value, option) for option in wanted)
        return cls._matches_one(value, wanted)

    def find(self, **conditions):
        """Return the menu variants matching every condition, without printing.

        Each keyword is a field of the API's variant data (``Name``,
        ``SizeCode``, ``ProductCode``, ...) and each value is matched as a
        case-insensitive substring::

            menu.find(Name='coke')

        A list or tuple matches any one of its values::

            menu.find(SizeCode=['12', '14'])

        Returns:
            list: The matching variants, each a copy of the API's data with a
            parsed ``Toppings`` dict added.
        """
        results = []
        for variant in self.variants.values():
            if all(self._matches(variant.get(field, ''), wanted)
                   for field, wanted in conditions.items()):
                match = dict(variant)
                match['Toppings'] = self.parse_toppings(variant)
                results.append(match)
        return results

    def search(self, **conditions):
        """Print the menu variants matching every condition, and return them.

        Takes the same conditions as :meth:`find`, prints the matches as an
        aligned ``code  name  price`` table, and returns them so callers can do
        something other than read them::

            codes = [item['Code'] for item in menu.search(Name='Coke')]
        """
        results = self.find(**conditions)
        print(self.format_results(results))
        return results

    @staticmethod
    def format_results(results):
        """Render search results as an aligned ``code  name  price`` table."""
        if not results:
            return ''
        width = lambda field: 2 + max(len(str(item.get(field, ''))) for item in results)
        return '\n'.join(
            '{code:<{code_width}}{name:<{name_width}}${price}'.format(
                code=item.get('Code', ''), code_width=width('Code'),
                name=item.get('Name', ''), name_width=width('Name'),
                price=item.get('Price', ''),
            )
            for item in results
        )
