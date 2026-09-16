import pytest
from mock import MagicMock, patch

from pizzapy import utils
from pizzapy.utils import (
    DEFAULT_TIMEOUT,
    looks_like_postal_code,
    post_json,
    request_json,
    request_xml,
)

SOAP = '''<?xml version="1.0"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body><Reply>ok</Reply></soap:Body>
</soap:Envelope>'''


@pytest.fixture
def session():
    """Swap in a fake session, and put the real one back afterwards."""
    fake = MagicMock()
    fake.get.return_value.json.return_value = {'Status': 0}
    fake.get.return_value.text = SOAP
    fake.post.return_value.json.return_value = {'Status': 0}
    utils.set_session(fake)
    yield fake
    utils.set_session(None)


def test_request_json_formats_the_url_and_returns_json(session):
    assert request_json('https://x/{store_id}/menu', store_id='4336') == {'Status': 0}
    assert session.get.call_args[0][0] == 'https://x/4336/menu'


def test_requests_always_carry_a_timeout(session):
    """Nothing set a timeout, so a slow endpoint could hang forever.

    That was the 'TODO: Find out why this occasionally hangs' in this module.
    """
    request_json('https://x/')
    assert session.get.call_args[1]['timeout'] == DEFAULT_TIMEOUT
    request_xml('https://x/')
    assert session.get.call_args[1]['timeout'] == DEFAULT_TIMEOUT
    post_json('https://x/', {'Order': {}})
    assert session.post.call_args[1]['timeout'] == DEFAULT_TIMEOUT


def test_the_timeout_can_be_overridden(session):
    request_json('https://x/', timeout=0.5)
    assert session.get.call_args[1]['timeout'] == 0.5


def test_errors_are_raised(session):
    session.get.return_value.raise_for_status.side_effect = ValueError('boom')
    with pytest.raises(ValueError):
        request_json('https://x/')


def test_request_xml_parses_the_response(session):
    parsed = request_xml('https://x/')
    assert parsed['soap:Envelope']['soap:Body']['Reply'] == 'ok'


def test_post_json_sends_the_payload_and_headers(session):
    payload = {'Order': {'StoreID': '4336'}}
    headers = {'Referer': 'https://order.dominos.com/en/pages/order/'}
    assert post_json('https://x/', payload, headers=headers) == {'Status': 0}
    assert session.post.call_args[1]['json'] == payload
    assert session.post.call_args[1]['headers'] == headers


def test_the_session_is_reused_between_calls():
    utils.set_session(None)
    try:
        assert utils.get_session() is utils.get_session()
    finally:
        utils.set_session(None)


def test_only_get_requests_are_retried():
    """Retrying a POST could place the same order twice."""
    utils.set_session(None)
    try:
        adapter = utils.get_session().get_adapter('https://order.dominos.com/')
        retry = adapter.max_retries
        allowed = getattr(retry, 'allowed_methods', None) or retry.method_whitelist
        assert set(allowed) == {'GET'}
        assert retry.total == utils.DEFAULT_RETRIES
        assert 503 in retry.status_forcelist
    finally:
        utils.set_session(None)


@patch('pizzapy.utils.requests.Session')
def test_a_custom_session_is_left_alone(Session, session):
    """set_session should not be overwritten by the built-in one."""
    request_json('https://x/')
    Session.assert_not_called()


@pytest.mark.parametrize('value,expected', [
    ('20408', True),
    ('20408-1234', True),
    ('M5E 1E5', True),
    ('M5E1E5', True),
    ('m5e-1e5', True),
    (' 20408 ', True),
    ('2040', False),
    ('DC', False),
    ('', False),
    (20408, True),
])
def test_looks_like_postal_code(value, expected):
    assert looks_like_postal_code(value) is expected
