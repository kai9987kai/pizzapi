import pytest
from mock import patch

from pizzapy import cli

ADDRESS = '700 Pennsylvania Avenue NW, Washington, DC, 20408'


def test_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(['--version'])
    assert excinfo.value.code == 0
    assert 'pizzapy' in capsys.readouterr().out


def test_no_command_is_an_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([])
    assert excinfo.value.code != 0


def test_stores_lists_what_it_found(stores_data, capsys):
    with patch('pizzapy.address.request_json', return_value=stores_data):
        assert cli.main(['stores', ADDRESS]) == 0
    out = capsys.readouterr().out
    assert '[4336]' in out
    assert '202-639-8700' in out
    assert '1300 L St Nw, Washington, DC 20005' in out


def test_stores_reports_when_nothing_is_open(capsys):
    with patch('pizzapy.address.request_json', return_value={'Stores': []}):
        assert cli.main(['stores', ADDRESS]) == 1
    assert 'No stores' in capsys.readouterr().out


def test_stores_passes_the_service_through(stores_data):
    with patch('pizzapy.address.request_json', return_value=stores_data) as request:
        cli.main(['stores', ADDRESS, '--service', 'Carryout'])
    assert request.call_args[1]['type'] == 'Carryout'


def test_country_reaches_the_api(stores_data):
    with patch('pizzapy.address.request_json', return_value=stores_data) as request:
        cli.main(['--country', 'ca', 'stores', '1 Yonge St, Toronto, ON, M5E 1E5'])
    assert '.ca/' in request.call_args[0][0]


def test_menu_by_store_id(menu_data, capsys):
    with patch('pizzapy.store.request_json', return_value=menu_data) as request:
        assert cli.main(['menu', '--store', '4336']) == 0
    assert request.call_args[1]['store_id'] == '4336'
    assert 'Regular Menu' in capsys.readouterr().out


def test_menu_search(menu_data, capsys):
    with patch('pizzapy.store.request_json', return_value=menu_data):
        assert cli.main(['menu', '--store', '4336', '--search', 'coke']) == 0
    out = capsys.readouterr().out
    assert '20BCOKE' in out
    assert 'Regular Menu' not in out


def test_menu_search_with_no_matches(menu_data, capsys):
    with patch('pizzapy.store.request_json', return_value=menu_data):
        assert cli.main(['menu', '--store', '4336', '--search', 'sushi']) == 1
    assert 'Nothing on the menu' in capsys.readouterr().out


def test_menu_finds_the_closest_store_to_an_address(stores_data, menu_data, capsys):
    with patch('pizzapy.address.request_json', return_value=stores_data), \
            patch('pizzapy.store.request_json', return_value=menu_data) as menu_call:
        assert cli.main(['menu', ADDRESS, '--search', 'coke']) == 0
    assert menu_call.call_args[1]['store_id'] == '4336'
    assert 'Store #4336' in capsys.readouterr().err


def test_menu_needs_a_source(capsys):
    with pytest.raises(SystemExit):
        cli.main(['menu'])


def test_track_by_phone(capsys):
    with patch('pizzapy.cli.track_by_phone', return_value={'Status': 'Delivered'}) as track:
        assert cli.main(['track', '--phone', '2024561111']) == 0
    assert track.call_args[0] == ('2024561111', 'us')
    assert 'Delivered' in capsys.readouterr().out


def test_track_by_order(capsys):
    with patch('pizzapy.cli.track_by_order', return_value={'Status': 'Baking'}) as track:
        assert cli.main(['track', '--store', '4336', '--order', 'KEY']) == 0
    assert track.call_args[0] == ('4336', 'KEY', 'us')


def test_track_without_enough_information(capsys):
    assert cli.main(['track']) == 2
    assert 'Pass --phone' in capsys.readouterr().err


def test_library_errors_become_clean_messages(capsys):
    """A user should see a message, not a traceback."""
    with patch('pizzapy.address.request_json', return_value={'Stores': []}):
        assert cli.main(['menu', ADDRESS]) == 1
    err = capsys.readouterr().err
    assert 'error:' in err
    assert 'Traceback' not in err


def test_the_cli_cannot_place_an_order():
    """Ordering is deliberately not exposed: a typo should not cost money."""
    help_text = cli.build_parser().format_help()
    assert 'order' not in help_text.lower().split('track')[0]
    assert set(cli.COMMANDS) == {'stores', 'menu', 'track'}
