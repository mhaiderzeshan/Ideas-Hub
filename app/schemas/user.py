from pydantic import BaseModel, constr
from typing import Annotated
import enum


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
    id: int
    name: str
    email: str
    role: UserRole = UserRole.user

    class Config:
        from_attributes = True
