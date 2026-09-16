from .address import Address
from .urls import COUNTRY_USA


class Customer(object):
    """The Customer who orders a pizza.

    Attributes:
        first_name (str): The customer's first name
        last_name (str): The customer's last name
        email (str): Where the confirmation email is sent
        phone (str): The customer's phone number
        address (Address): Where the order is delivered
    """

    def __init__(self, fname='', lname='', email='', phone='', address=None,
                 country=COUNTRY_USA):
        self.first_name = str(fname).strip()
        self.last_name = str(lname).strip()
        self.email = str(email).strip()
        self.phone = str(phone).strip()
        self.address = self._coerce_address(address, country)

    @staticmethod
    def _coerce_address(address, country):
        """Accept an Address, a comma-separated string, or nothing."""
        if address is None or isinstance(address, Address):
            return address
        return Address.from_string(address, country)

    @property
    def full_name(self):
        return ' '.join(part for part in (self.first_name, self.last_name) if part)

    def __repr__(self):
        return "Name: {} {}\nEmail: {}\nPhone: {}\nAddress: {}".format(
            self.first_name,
            self.last_name,
            self.email,
            self.phone,
            self.address,
        )
