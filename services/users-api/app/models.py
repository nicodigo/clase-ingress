from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    email: str


class User(UserCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
