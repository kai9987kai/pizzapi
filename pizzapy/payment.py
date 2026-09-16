import datetime
import re

from .utils import looks_like_postal_code


class CreditCard(object):
    """A CreditCard represents a credit card.

    The card type is worked out from the number, and :meth:`validate` checks
    that every field is well formed before you hand the card to an order.

    Attributes:
        number (str): The card number, with spaces and dashes removed
        expiration (str): The expiry date as ``MMYY``
        cvv (str): The 3 or 4 digit security code
        zip (str): The billing ZIP or postal code
        card_type (str): The detected network, e.g. ``VISA``. Empty if unknown.
    """

    #: Card number patterns, most specific first.
    PATTERNS = {
        'VISA': r'^4[0-9]{12}(?:[0-9]{3})?$',
        # 51-55 is the old MasterCard range; 2221-2720 was added in 2016.
        'MASTERCARD': r'^(?:5[1-5][0-9]{14}|2(?:22[1-9]|2[3-9][0-9]|[3-6][0-9]{2}|7[0-1][0-9]|720)[0-9]{12})$',
        'AMEX': r'^3[47][0-9]{13}$',
        'DINERS': r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$',
        'DISCOVER': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
        'JCB': r'^(?:2131|1800|35\d{3})\d{11}$',
        'ENROUTE': r'^(?:2014|2149)\d{11}$',
    }

    def __init__(self, number='', expiration='', cvv='', zip=''):
        self.name = ''
        # Accept the way people actually read a card out: "4100 1234 2234 3234".
        self.number = re.sub(r'[\s-]', '', str(number).strip())
        self.card_type = self.find_type()
        self.expiration = re.sub(r'[\s/-]', '', str(expiration).strip())
        self.cvv = str(cvv).strip()
        self.zip = str(zip).strip()

    def __repr__(self):
        return "Credit Card with last four #{}".format(self.number[-4:])

    def validate(self):
        """Return True if every field is well formed.

        Checks the number's length, network and Luhn checksum, plus the format
        of the expiry date, security code and billing postal code. Expiry
        *dates* are not compared against today; use :meth:`is_expired` for that.

        Earlier versions raised ``TypeError`` here for every card, valid or
        not, because they combined a string and a regex match with ``&``.
        """
        return bool(
            self.number
            and self.card_type
            and self.luhn_valid()
            and re.match(r'^(?:0[1-9]|1[0-2])[0-9]{2}$', self.expiration)
            and re.match(r'^[0-9]{3,4}$', self.cvv)
            and looks_like_postal_code(self.zip)
        )

    def luhn_valid(self):
        """Return True if the number passes the Luhn checksum."""
        if not self.number.isdigit():
            return False
        digits = [int(d) for d in reversed(self.number)]
        total = sum(digits[0::2])
        total += sum(sum(divmod(d * 2, 10)) for d in digits[1::2])
        return total % 10 == 0

    def is_expired(self, today=None):
        """Return True if the card's ``MMYY`` expiry is in the past.

        Cards are good through the last day of their expiry month. Returns
        False for an unparseable expiry; :meth:`validate` is what rejects those.
        """
        if not re.match(r'^(?:0[1-9]|1[0-2])[0-9]{2}$', self.expiration):
            return False
        today = today or datetime.date.today()
        month, year = int(self.expiration[:2]), 2000 + int(self.expiration[2:])
        return (year, month) < (today.year, today.month)

    def find_type(self):
        """Return the card's network, or '' if the number matches none."""
        return next((card_type for card_type, pattern in self.PATTERNS.items()
                     if re.match(pattern, self.number)), '')
