from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentResult:
    user_id: int
    amount: Decimal
    status: str


def make_payment(user_id: int, amount: Decimal) -> PaymentResult:
    if amount <= Decimal("0"):
        raise ValueError("payment amount must be greater than zero")
    return PaymentResult(user_id=user_id, amount=amount, status="authorized")
