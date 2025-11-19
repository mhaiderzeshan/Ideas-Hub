from pydantic import BaseModel, constr
from typing import Annotated
import enum
from uuid import UUID


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserBase(BaseModel):
    name: str
    email: str


class UserCreate(UserBase):
    password: Annotated[str, constr(min_length=8)]


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole = UserRole.user
    is_email_verified: bool = False
    email_verified_at: bool = False
    created_at: str
    last_login_at: str | None = None

    class Config:
        from_attributes = True
