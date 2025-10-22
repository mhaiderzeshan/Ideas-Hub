from pydantic import BaseModel, constr
from typing import Annotated
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole = UserRole.user


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


"""class IdeaBase(BaseModel):
    title: Annotated[str, constr(max_length=255)]
    description: str | None = None


class IdeaCreate(IdeaBase):
    pass


class Idea(IdeaBase):
    id: int
    owner_id: int
    created_at: datetime

    class Config:
        orm_mode = True"""


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str
