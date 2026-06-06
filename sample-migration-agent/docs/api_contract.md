# Sample API Contract

The public JSON response fields are stable migration contracts.

## UserResponse

`get_user_response()` and `GET /users/123` must return:

```json
{
  "user_id": 123,
  "full_name": "Ada Lovelace",
  "created_at": "2026-01-01T09:30:00"
}
```

Forbidden leaked fields:

- `id`
- `name`

## OrderResponse

`get_order_response()` and `GET /orders/ord_123` must return:

```json
{
  "order_id": "ord_123",
  "user_id": 123,
  "total_cents": 2599,
  "created_at": "2026-01-02T10:00:00"
}
```

Forbidden leaked field:

- `id`

## Validation Semantics

- Blank `full_name` values must raise a Pydantic `ValidationError`.
- `total_cents <= 0` must raise a Pydantic `ValidationError`.
- `make_payment(user_id, Decimal("0"))` must raise `ValueError`.
