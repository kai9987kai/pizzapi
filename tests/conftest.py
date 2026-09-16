"""Fixtures shared by the whole test suite.

Paths are resolved relative to this file, so the suite runs from any
working directory rather than only from the repository root.
"""
import json
import os

import pytest

from pizzapy.customer import Customer
from pizzapy.menu import Menu
from pizzapy.order import Order
from pizzapy.store import Store

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def load_fixture(name):
    with open(os.path.join(FIXTURE_DIR, name)) as fp:
        return json.load(fp)


@pytest.fixture(scope='session')
def menu_data():
    return load_fixture('menu.json')


@pytest.fixture(scope='session')
def stores_data():
    return load_fixture('stores.json')


@pytest.fixture
def menu(menu_data):
    return Menu(menu_data)


@pytest.fixture
def store(stores_data):
    return Store(stores_data['Stores'][0])


@pytest.fixture
def customer():
    return Customer(
        'Barack', 'Obama', 'barack@whitehouse.gov', '2024561111',
        '700 Pennsylvania Avenue NW, Washington, DC, 20408',
    )


@pytest.fixture
def order(store, customer, menu):
    """An order with the menu supplied, so no network call is made."""
    return Order(store, customer, menu=menu)
