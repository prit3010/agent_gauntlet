from decimal import Decimal

import pytest

from app.payments import make_payment


def test_make_payment_rejects_zero_amount():
    with pytest.raises(ValueError):
        make_payment(user_id=123, amount=Decimal("0"))

