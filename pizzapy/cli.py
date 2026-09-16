"""A small command line tool for looking things up.

Deliberately read-only: it finds stores, reads menus and tracks orders, but
it cannot place an order. Spending money should take more than a typo.
"""
from __future__ import print_function

import argparse
import sys

from . import __version__
from .address import Address
from .exceptions import PizzaPyError
from .menu import Menu
from .store import Store
from .track import track_by_order, track_by_phone
from .urls import COUNTRIES, COUNTRY_USA


def build_parser():
    parser = argparse.ArgumentParser(
        prog='pizzapy',
        description="Look up Domino's stores, menus and orders.",
    )
    parser.add_argument('--version', action='version',
                        version='pizzapy {}'.format(__version__))
    parser.add_argument('--country', default=COUNTRY_USA, choices=COUNTRIES,
                        help='which country to query (default: %(default)s)')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.required = True

    stores = subparsers.add_parser('stores', help='list stores near an address')
    stores.add_argument('address', help='e.g. "700 Pennsylvania Ave NW, Washington, DC, 20408"')
    stores.add_argument('--service', default='Delivery', choices=('Delivery', 'Carryout'))

    menu = subparsers.add_parser('menu', help="show a store's menu")
    source = menu.add_mutually_exclusive_group(required=True)
    source.add_argument('address', nargs='?', help='find the closest store to this address')
    source.add_argument('--store', help='use this store ID directly')
    menu.add_argument('--search', metavar='TEXT', help='only show items matching TEXT')
    menu.add_argument('--service', default='Delivery', choices=('Delivery', 'Carryout'))

    track = subparsers.add_parser('track', help='track an order')
    track.add_argument('--phone', help='the phone number the order was placed with')
    track.add_argument('--store', help='the store the order was placed at')
    track.add_argument('--order', help='the order key, used with --store')

    return parser


def _closest_store(address, country, service):
    return Address.from_string(address, country).closest_store(service=service)


def cmd_stores(args):
    stores = Address.from_string(args.address, args.country).nearby_stores(
        service=args.service
    )
    if not stores:
        print('No stores near that address are open for {}.'.format(args.service))
        return 1
    for store in stores:
        print('[{}] {}  {}'.format(
            store.id, store.phone or 'no phone',
            store.address_description.replace('\n', ', '),
        ))
    return 0


def cmd_menu(args):
    if args.store:
        store = Store({'StoreID': args.store}, args.country)
    else:
        store = _closest_store(args.address, args.country, args.service)
        print('Store #{}'.format(store.id), file=sys.stderr)

    menu = store.get_menu()
    if args.search:
        results = menu.find(Name=args.search)
        if not results:
            print('Nothing on the menu matches {!r}.'.format(args.search))
            return 1
        print(Menu.format_results(results))
    else:
        menu.display()
    return 0


def cmd_track(args):
    if args.phone:
        print(track_by_phone(args.phone, args.country))
    elif args.store and args.order:
        print(track_by_order(args.store, args.order, args.country))
    else:
        print('Pass --phone, or both --store and --order.', file=sys.stderr)
        return 2
    return 0


COMMANDS = {'stores': cmd_stores, 'menu': cmd_menu, 'track': cmd_track}


def main(argv=None):
    """Run the CLI. Returns the process exit code."""
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.command](args)
    except PizzaPyError as error:
        print('error: {}'.format(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
