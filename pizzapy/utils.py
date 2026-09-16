"""Helpers shared by the rest of the library.

Every network call pizzapy makes goes through this module, so timeouts,
retries and connection reuse are configured in exactly one place. The small
shared validators live here too, so address and payment agree on what a
postal code looks like.
"""
import re

import requests
import xmltodict
from requests.adapters import HTTPAdapter

try:  # urllib3 >= 1.26 ships the retry helper at this path
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover - very old requests vendored urllib3
    from requests.packages.urllib3.util.retry import Retry

#: Seconds to wait for the API before giving up. Domino's endpoints are
#: occasionally slow to answer and requests has no default timeout, so
#: without this a call could hang forever.
DEFAULT_TIMEOUT = 15.0

#: How many times to retry a *read-only* request that failed in a way that
#: tends to be transient.
DEFAULT_RETRIES = 2

#: Responses worth retrying: rate limiting and the 5xx family.
RETRY_STATUSES = (429, 500, 502, 503, 504)

_session = None


def _build_session():
    session = requests.Session()
    retry_kwargs = dict(
        total=DEFAULT_RETRIES,
        backoff_factor=0.3,
        status_forcelist=RETRY_STATUSES,
        raise_on_status=False,
    )
    # Only GET is retried. Retrying a POST could place an order twice.
    try:
        retry = Retry(allowed_methods=frozenset(['GET']), **retry_kwargs)
    except TypeError:  # pragma: no cover - urllib3 < 1.26 spelling
        retry = Retry(method_whitelist=frozenset(['GET']), **retry_kwargs)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


def get_session():
    """Return the shared :class:`requests.Session` used for API calls.

    Reusing one session keeps connections alive between calls and applies the
    retry policy above. Replace it with :func:`set_session` if you need your
    own configuration (a proxy, custom headers, a test double).
    """
    global _session
    if _session is None:
        _session = _build_session()
    return _session


def set_session(session):
    """Install a :class:`requests.Session` for pizzapy to use.

    Pass ``None`` to go back to the default session.
    """
    global _session
    _session = session


def _request(url, timeout=DEFAULT_TIMEOUT, **kwargs):
    """GET ``url``, formatted with ``kwargs``, and return the response.

    This is the single place every read-only request goes through, so callers
    do not have to care about sessions, timeouts or retries.

    Raises:
        requests.HTTPError: If the API answered with an error status.
    """
    response = get_session().get(url.format(**kwargs), timeout=timeout)
    response.raise_for_status()
    return response


def request_json(url, timeout=DEFAULT_TIMEOUT, **kwargs):
    """Send a GET request to one of the API endpoints that returns JSON.

    Send a GET request to an endpoint, ideally a URL from the urls module.
    The endpoint is formatted with the kwargs passed to it.

    This will error on an invalid request (``requests.Response.raise_for_status``),
    but will otherwise return a dict.
    """
    return _request(url, timeout=timeout, **kwargs).json()


def request_xml(url, timeout=DEFAULT_TIMEOUT, **kwargs):
    """Send a GET request to one of the API endpoints that returns XML.

    This is in every respect identical to :func:`request_json`, except that
    the response is parsed as XML into a dict.
    """
    return xmltodict.parse(_request(url, timeout=timeout, **kwargs).text)


def post_json(url, payload, headers=None, timeout=DEFAULT_TIMEOUT):
    """POST ``payload`` as JSON and return the decoded response.

    Unlike the GET helpers this never retries: a retried order could be an
    order placed twice.

    Raises:
        requests.HTTPError: If the API answered with an error status.
    """
    response = get_session().post(
        url=url, headers=headers, json=payload, timeout=timeout
    )
    response.raise_for_status()
    return response.json()


#: A US ZIP ("20408", "20408-1234") or a Canadian postal code ("M5E 1E5").
POSTAL_CODE_RE = re.compile(
    r'^(?:[0-9]{5}(?:-[0-9]{4})?|[A-Za-z][0-9][A-Za-z][ -]?[0-9][A-Za-z][0-9])$'
)


def looks_like_postal_code(value):
    """Return True if ``value`` looks like a US ZIP or Canadian postal code."""
    return bool(POSTAL_CODE_RE.match(str(value).strip()))
