from pydantic import BaseModel, constr, EmailStr
from typing import Annotated
import enum
from uuid import UUID
from datetime import datetime


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    password: Annotated[str, constr(min_length=8)]


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole = UserRole.user
    is_email_verified: bool = False
    email_verified_at: datetime | None = None
    created_at: datetime
    last_login_at: datetime | None = None

    class Config:
        from_attributes = True
