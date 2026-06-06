from decimal import Decimal
from inspect import signature

import pytest

from app.payments import PaymentResult, make_payment


def test_make_payment_rejects_zero_amount():
    with pytest.raises(ValueError, match="greater than zero"):
        make_payment(user_id=123, amount=Decimal("0"))


def test_make_payment_rejects_negative_amount():
    with pytest.raises(ValueError, match="greater than zero"):
        make_payment(user_id=123, amount=Decimal("-1.00"))


def test_make_payment_authorizes_positive_amount():
    result = make_payment(user_id=123, amount=Decimal("12.50"))

    assert result == PaymentResult(user_id=123, amount=Decimal("12.50"), status="authorized")


def test_make_payment_public_signature_is_stable():
    params = signature(make_payment).parameters

    assert list(params) == ["user_id", "amount"]
    assert str(params["user_id"].annotation) == "<class 'int'>"
    assert str(params["amount"].annotation) == "<class 'decimal.Decimal'>"
