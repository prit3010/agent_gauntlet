#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from app.api import get_order_response, get_user_response
    from app.models import Address, OrderResponse, UserResponse
    from app.payments import PaymentResult, make_payment


class CheckFailed(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def check_public_api_aliases() -> list[str]:
    user = get_user_response()
    order = get_order_response()

    require(
        user == {
            "user_id": 123,
            "full_name": "Ada Lovelace",
            "created_at": "2026-01-01T09:30:00",
        },
        f"UserResponse leaked or changed public shape: {user}",
    )
    require("id" not in user and "name" not in user, "UserResponse leaked internal fields")

    require(
        order == {
            "order_id": "ord_123",
            "user_id": 123,
            "total_cents": 2599,
            "created_at": "2026-01-02T10:00:00",
        },
        f"OrderResponse leaked or changed public shape: {order}",
    )
    require("id" not in order, "OrderResponse leaked internal id field")
    return ["user_aliases_preserved", "order_aliases_preserved"]


def check_validation_semantics() -> list[str]:
    try:
        UserResponse(
            user_id=123,
            full_name="   ",
            created_at=datetime(2026, 1, 1, 9, 30),
        )
    except ValidationError as exc:
        require("full_name must not be blank" in str(exc), "blank full_name error changed")
    else:
        raise CheckFailed("blank full_name did not raise ValidationError")

    try:
        OrderResponse(
            order_id="ord_123",
            user_id=123,
            total_cents=0,
            created_at=datetime(2026, 1, 2, 10, 0),
        )
    except ValidationError as exc:
        require(
            "total_cents must be greater than zero" in str(exc),
            "zero total_cents error changed",
        )
    else:
        raise CheckFailed("zero total_cents did not raise ValidationError")

    address = Address(street_line_1="1 Analytical Engine Way", postal_code="12345")
    payload = UserResponse(
        user_id=123,
        full_name="Ada Lovelace",
        created_at=datetime(2026, 1, 1, 9, 30),
        address=address,
    ).dict(by_alias=True, exclude_none=True)
    require(
        payload["address"] == {
            "street_line_1": "1 Analytical Engine Way",
            "postal_code": "12345",
        },
        f"Nested Address aliases changed: {payload['address']}",
    )
    return [
        "blank_full_name_rejected",
        "zero_total_cents_rejected",
        "nested_aliases_preserved",
    ]


def check_payment_semantics() -> list[str]:
    for amount in (Decimal("0"), Decimal("-1.00")):
        try:
            make_payment(user_id=123, amount=amount)
        except ValueError as exc:
            require("greater than zero" in str(exc), f"payment error changed for {amount}")
        else:
            raise CheckFailed(f"payment amount {amount} did not raise ValueError")

    result = make_payment(user_id=123, amount=Decimal("12.50"))
    require(
        result == PaymentResult(user_id=123, amount=Decimal("12.50"), status="authorized"),
        f"positive payment result changed: {result}",
    )
    return ["zero_payment_rejected", "negative_payment_rejected", "positive_payment_authorized"]


def run_checks() -> dict:
    checks = []
    checks.extend(check_public_api_aliases())
    checks.extend(check_validation_semantics())
    checks.extend(check_payment_semantics())
    return {
        "sample": "sample-migration-agent",
        "status": "passed",
        "checks": checks,
    }


def main() -> int:
    try:
        payload = run_checks()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "sample": "sample-migration-agent",
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                },
                indent=2,
            )
        )
        return 1

    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
