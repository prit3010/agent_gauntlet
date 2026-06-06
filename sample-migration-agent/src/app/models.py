from datetime import datetime
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int = Field(alias="user_id")
    name: str = Field(alias="full_name")
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


class OrderResponse(BaseModel):
    id: int = Field(alias="order_id")
    total_cents: int
    created_at: datetime

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

