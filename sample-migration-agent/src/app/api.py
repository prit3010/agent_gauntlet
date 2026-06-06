from datetime import datetime

from .models import UserResponse


def get_user_response() -> dict:
    user = UserResponse(user_id=123, full_name="Ada Lovelace", created_at=datetime(2026, 1, 1))
    return user.dict(by_alias=True)

