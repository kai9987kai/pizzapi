pizzapy
=======

A Python wrapper for the Domino's Pizza API.

This is a fork of `gamagori/pizzapi <https://github.com/gamagori/pizzapi>`_,
itself a port of `the pizzapi node.js module
<https://github.com/RIAEvangelist/node-dominos-pizza-api>`_ written by
`RIAEvangelist <https://github.com/RIAEvangelist>`_.

Both the United States (``us``) and Canada (``ca``) are supported.

Setup
-----

.. code-block:: shell

    pip install -r requirements.txt
    pip install -e .

Python 3.6 or newer. The library itself only needs ``requests`` and
``xmltodict``; the rest of ``requirements.txt`` is for running the tests.

Quick Start
-----------

First construct a ``Customer`` object and set the customer's address:

.. code-block:: python

    from pizzapy import Customer, Order, StoreLocator
    from pizzapy.payment import CreditCard

    customer = Customer('Barack', 'Obama', 'barack@whitehouse.gov', '2024561111',
                        '700 Pennsylvania Avenue NW, Washington, DC, 20408')

The address is read as ``street, city, region, ZIP``. Extra street fields are
kept with the street, so ``'123 Main St, Apt 4, Springfield, IL, 62704'`` works
too, and you can pass an ``Address`` object instead if you would rather build
it yourself.

Then, find a store that will deliver to the address.

.. code-block:: python

    my_local_dominos = StoreLocator.find_closest_store_to_customer(customer)

In order to add items to your order, you'll need the items' product codes.
To find the codes, get the menu from the store, then search for items you want
to add. You can do this by asking your ``Store`` object for its ``Menu``.

.. code-block:: python

    menu = my_local_dominos.get_menu()

Then search ``menu`` with ``menu.search``. For example, running this command:

.. code-block:: python

    menu.search(Name='Coke')

Should print this to the console:

.. code-block:: text

    20BCOKE    20oz Bottle Coke®        $1.89
    20BDCOKE   20oz Bottle Diet Coke®   $1.89
    D20BZRO    20oz Bottle Coke Zero™   $1.89
    2LDCOKE    2-Liter Diet Coke®       $2.99
    2LCOKE     2-Liter Coke®            $2.99

Searching is case insensitive, and every condition has to match. A list matches
any one of its values:

.. code-block:: python

    menu.search(Name='pizza', SizeCode=['12', '14'])

``search`` also *returns* what it found, so you can use the results rather than
just read them. Use ``menu.find`` for the same search without the printing:

.. code-block:: python

    codes = [item['Code'] for item in menu.find(Name='Coke')]

After you've found your items' product codes, you can create an ``Order``
object and add your items:

.. code-block:: python

    order = Order.begin_customer_order(customer, my_local_dominos, menu=menu)
    order.add_item('P12IPAZA') # add a 12-inch pan pizza
    order.add_item('MARINARA') # with an extra marinara cup
    order.add_item('20BCOKE')  # and a 20oz bottle of coke

Passing ``menu=menu`` reuses the menu you already downloaded. Leave it out and
the order fetches its own.

You can add toppings, remove items, and add coupons as well:

.. code-block:: python

    order.add_item('P12IPAZA', qty=2, options=['P', 'X'])  # pepperoni and extra cheese
    order.remove_item('20BCOKE')
    order.add_coupon('9174')

Check what it all comes to before you commit to anything:

.. code-block:: python

    order.price()   # {'Customer': 26.94, 'Tax': 1.95, ...}

Wrap your credit card information in a ``CreditCard``:

.. code-block:: python

    card = CreditCard('4100 1234 2234 3237', '0130', '777', '90210')
    card.validate()   # checks the number, its checksum, and every other field
    card.is_expired() # checks the expiry date against today

Spaces and dashes in the number are fine, and so is ``01/30`` for the expiry.

And that's it! Now you can place your order.

.. code-block:: python

    order.place(card)
    my_local_dominos.place_order(order, card)

Ordering outside the USA
------------------------

Pass a country and every request — store lookup, menu, pricing and placing —
goes to that country's endpoints:

.. code-block:: python

    from pizzapy import COUNTRY_CANADA

    customer = Customer('Barack', 'Obama', 'barack@whitehouse.gov', '2024561111',
                        '1 Yonge St, Toronto, ON, M5E 1E5', country=COUNTRY_CANADA)

Tracking an order
-----------------

.. code-block:: python

    from pizzapy import track_by_phone, track_by_order

    track_by_phone('2024561111')
    track_by_order(store_id='4336', order_key='...')

When things go wrong
--------------------

Everything this library raises deliberately derives from ``PizzaPyError``, so
one ``except`` covers the lot:

.. code-block:: python

    from pizzapy import PizzaPyError, StoreNotFoundError, ItemNotFoundError, OrderError

    try:
        order.place(card)
    except OrderError as error:
        print(error)            # what the API objected to
        print(error.response)   # the full response, if there was one

``StoreNotFoundError`` means nothing nearby is open, ``ItemNotFoundError``
means a product code isn't on the menu or in the order, and
``InvalidCountryError`` / ``InvalidAddressError`` mean the address couldn't be
used. They also derive from the builtin they replaced (``KeyError``,
``ValueError``), so existing handlers keep working.

Command line
------------

Installing the package adds a ``pizzapy`` command for looking things up. It is
read-only on purpose — it will not place an order:

.. code-block:: shell

    pizzapy stores "700 Pennsylvania Avenue NW, Washington, DC, 20408"
    pizzapy menu --store 4336 --search coke
    pizzapy --country ca menu "1 Yonge St, Toronto, ON, M5E 1E5"
    pizzapy track --phone 2024561111

Running the tests
-----------------

.. code-block:: shell

    python -m pytest

The suite never touches the network — every API response is a recorded fixture.
