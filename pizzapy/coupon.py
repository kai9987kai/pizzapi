class Coupon(object):
    """Loose representation of a coupon.

    Add one to an order with :meth:`pizzapy.order.Order.add_coupon`, which
    takes the coupon's code. Fetch a coupon's terms — what you have to order
    for it to apply — with :meth:`pizzapy.store.Store.get_coupon`.

    Attributes:
        code (str): The coupon's code, as it appears on the menu
        quantity (int): How many times to apply it
    """

    def __init__(self, code, quantity=1):
        self.code = code
        self.quantity = quantity
        self.id = 1
        self.is_new = True

    def __repr__(self):
        return 'Coupon({!r}, quantity={!r})'.format(self.code, self.quantity)

    @property
    def data(self):
        """The coupon in the shape the ordering API expects."""
        return {'Code': self.code, 'Qty': self.quantity,
                'ID': self.id, 'isNew': self.is_new}
