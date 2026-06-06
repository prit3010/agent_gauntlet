from app.api import get_user_response


def test_user_response_uses_public_aliases():
    response = get_user_response()

    assert "user_id" in response
    assert "full_name" in response
    assert "created_at" in response
    assert "id" not in response
    assert "name" not in response

