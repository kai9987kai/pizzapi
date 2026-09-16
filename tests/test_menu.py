import pytest
from mock import patch

from pizzapy.exceptions import ItemNotFoundError
from pizzapy.menu import Menu
from pizzapy.urls import COUNTRY_CANADA, COUNTRY_USA, Urls

PAN_PIZZA = 'P12IPAZA'


@patch('pizzapy.menu.request_json')
def test_from_store_calls_the_menu_endpoint(request_json, menu_data):
    request_json.return_value = menu_data
    menu = Menu.from_store(store_id='4336', lang='en')
    request_json.assert_called_once_with(
        Urls(COUNTRY_USA).menu_url(), store_id='4336', lang='en'
    )
    assert menu.variants


@patch('pizzapy.menu.request_json')
def test_from_store_keeps_the_country(request_json, menu_data):
    """The country argument was accepted, then dropped on the floor."""
    request_json.return_value = menu_data
    menu = Menu.from_store(store_id='4336', country=COUNTRY_CANADA)
    assert '.ca/' in request_json.call_args[0][0]
    assert menu.country == COUNTRY_CANADA


def test_country_is_not_hardcoded_to_the_usa(menu_data):
    assert Menu(menu_data, COUNTRY_CANADA).country == COUNTRY_CANADA


def test_an_empty_menu_is_harmless():
    menu = Menu()
    assert menu.variants == {}
    assert menu.find(Name='Coke') == []


def test_categories_are_built(menu):
    assert set(menu.root_categories) >= {'Food', 'Coupons', 'PreconfiguredProducts'}
    assert menu.root_categories['Food'].subcategories
    assert menu.menu_by_code


def test_category_path_walks_up_to_the_root(menu):
    food = menu.root_categories['Food']
    pizza = next(c for c in food.subcategories if c.subcategories)
    child = pizza.subcategories[0]
    assert child.get_category_path() == food.code + pizza.code + child.code
    assert child.parent is pizza


def test_find_is_case_insensitive(menu):
    """search(Name='coke') used to return nothing at all."""
    assert [i['Code'] for i in menu.find(Name='coke')] == \
           [i['Code'] for i in menu.find(Name='Coke')]
    assert len(menu.find(Name='coke')) == 5


def test_find_matches_every_condition(menu):
    results = menu.find(Name='Pan', SizeCode='12')
    assert results
    assert all('pan' in i['Name'].lower() and i['SizeCode'] == '12' for i in results)


def test_find_accepts_a_list_of_alternatives(menu):
    both = menu.find(Name='Pizza', SizeCode=['12', '14'])
    assert {i['SizeCode'] for i in both} == {'12', '14'}
    separately = menu.find(Name='Pizza', SizeCode='12') + menu.find(Name='Pizza', SizeCode='14')
    assert sorted(i['Code'] for i in both) == sorted(i['Code'] for i in separately)


def test_find_returns_data_not_just_printed_text(menu):
    codes = [item['Code'] for item in menu.find(Name='Coke')]
    assert PAN_PIZZA not in codes
    assert '20BCOKE' in codes


def test_find_does_not_mutate_the_menu(menu):
    """search() used to write a parsed Toppings key into the menu data."""
    before = dict(menu.variants[PAN_PIZZA])
    results = menu.find(Code=PAN_PIZZA)
    assert menu.variants[PAN_PIZZA] == before
    assert 'Toppings' not in menu.variants[PAN_PIZZA]
    assert results[0]['Toppings'] == {'X': '1', 'C': '1', 'Cp': '1'}


def test_search_prints_an_aligned_table(menu, capsys):
    menu.search(Name='Coke')
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 5
    # Every price starts in the same column.
    assert len({line.index('$') for line in lines}) == 1
    assert all(line.startswith(('20B', 'D20', '2LD', '2LC')) for line in lines)


def test_search_returns_its_results_too(menu, capsys):
    results = menu.search(Name='Coke')
    capsys.readouterr()
    assert [i['Code'] for i in results] == [i['Code'] for i in menu.find(Name='Coke')]


def test_search_with_no_matches_prints_nothing(menu, capsys):
    assert menu.search(Name='sushi') == []
    assert capsys.readouterr().out.strip() == ''


def test_get_variant_returns_the_item(menu):
    assert menu.get_variant(PAN_PIZZA)['Code'] == PAN_PIZZA


def test_get_variant_names_the_missing_code(menu):
    with pytest.raises(ItemNotFoundError) as excinfo:
        menu.get_variant('NOT_A_CODE')
    assert 'NOT_A_CODE' in str(excinfo.value)


def test_item_not_found_is_still_a_key_error(menu):
    """Looking a code up on the menu used to raise a plain KeyError."""
    with pytest.raises(KeyError):
        menu.get_variant('NOT_A_CODE')


def test_parse_toppings():
    assert Menu.parse_toppings({'Tags': {'DefaultToppings': 'X=1,C=1'}}) == {'X': '1', 'C': '1'}
    assert Menu.parse_toppings({'Tags': {'DefaultToppings': ''}}) == {}
    assert Menu.parse_toppings({}) == {}


def test_display_walks_every_section(menu, capsys):
    menu.display()
    out = capsys.readouterr().out
    assert 'Coupon Menu' in out
    assert 'Regular Menu' in out
    assert '[%s]' % PAN_PIZZA in out


def test_display_skips_sections_the_menu_does_not_have(capsys):
    Menu().display()
    assert capsys.readouterr().out == ''
