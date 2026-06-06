from app.api import get_order_response, get_user_response


def test_user_response_uses_exact_public_aliases():
    response = get_user_response()

    assert response["user_id"] == 123
    assert response["full_name"] == "Ada Lovelace"
    assert response["created_at"] == "2026-01-01T09:30:00"
    assert set(response) == {"user_id", "full_name", "created_at"}
    assert "id" not in response
    assert "name" not in response


def test_order_response_uses_exact_public_aliases():
    response = get_order_response()

    assert response["order_id"] == "ord_123"
    assert response["user_id"] == 123
    assert response["total_cents"] == 2599
    assert response["created_at"] == "2026-01-02T10:00:00"
    assert set(response) == {"order_id", "user_id", "total_cents", "created_at"}
    assert "id" not in response
