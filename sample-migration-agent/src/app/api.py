from datetime import datetime

from fastapi import FastAPI

from .models import OrderResponse, UserResponse

app = FastAPI(title="Migration Pilot Sample API")


def serialize_response(model: UserResponse | OrderResponse) -> dict:
    return model.dict(by_alias=True, exclude_none=True)


def get_user_response() -> dict:
    user = UserResponse(
        user_id=123,
        full_name="Ada Lovelace",
        created_at=datetime(2026, 1, 1, 9, 30),
    )
    return serialize_response(user)


def get_order_response() -> dict:
    order = OrderResponse(
        order_id="ord_123",
        user_id=123,
        total_cents=2599,
        created_at=datetime(2026, 1, 2, 10, 0),
    )
    return serialize_response(order)


@app.get("/users/{user_id}")
def read_user(user_id: int) -> dict:
    if user_id != 123:
        return {"detail": "not found"}
    return get_user_response()


@app.get("/orders/{order_id}")
def read_order(order_id: str) -> dict:
    if order_id != "ord_123":
        return {"detail": "not found"}
    return get_order_response()
