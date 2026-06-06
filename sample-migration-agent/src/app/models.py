from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, validator


def _serialize_datetimes(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _serialize_datetimes(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_datetimes(item) for item in value]
    return value


class PublicBaseModel(BaseModel):
    def dict(self, *args: Any, **kwargs: Any) -> dict:
        return _serialize_datetimes(super().dict(*args, **kwargs))


class Address(PublicBaseModel):
    street_line_1: str = Field(alias="street_line_1")
    postal_code: str = Field(alias="postal_code")

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
        orm_mode = True
        from_attributes = True


class UserResponse(PublicBaseModel):
    id: int = Field(alias="user_id")
    name: str = Field(alias="full_name")
    created_at: datetime
    address: Address | None = None

    @validator("name")
    def full_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("full_name must not be blank")
        return value

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
        orm_mode = True
        from_attributes = True


class OrderResponse(PublicBaseModel):
    id: str = Field(alias="order_id")
    user_id: int = Field(alias="user_id")
    total_cents: int
    created_at: datetime

    @validator("total_cents")
    def total_cents_must_be_greater_than_zero(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("total_cents must be greater than zero")
        return value

    class Config:
        allow_population_by_field_name = True
        populate_by_name = True
        orm_mode = True
        from_attributes = True
