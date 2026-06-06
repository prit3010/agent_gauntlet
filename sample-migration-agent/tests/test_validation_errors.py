from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import Address, OrderResponse, UserResponse


def test_user_response_rejects_blank_full_name():
    with pytest.raises(ValidationError) as exc_info:
        UserResponse(
            user_id=123,
            full_name="   ",
            created_at=datetime(2026, 1, 1, 9, 30),
        )

    assert "full_name must not be blank" in str(exc_info.value)


def test_order_response_rejects_zero_total_cents():
    with pytest.raises(ValidationError) as exc_info:
        OrderResponse(
            order_id="ord_123",
            user_id=123,
            total_cents=0,
            created_at=datetime(2026, 1, 2, 10, 0),
        )

    assert "total_cents must be greater than zero" in str(exc_info.value)


def test_nested_address_preserves_public_aliases():
    address = Address(street_line_1="1 Analytical Engine Way", postal_code="12345")
    payload = UserResponse(
        user_id=123,
        full_name="Ada Lovelace",
        created_at=datetime(2026, 1, 1, 9, 30),
        address=address,
    ).dict(by_alias=True, exclude_none=True)

    assert payload["address"] == {
        "street_line_1": "1 Analytical Engine Way",
        "postal_code": "12345",
    }
