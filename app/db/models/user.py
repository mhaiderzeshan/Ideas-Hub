from sqlalchemy import String, Enum, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.db.database import Base
from app.db.models.enum_json import UserRole
from app.db.models.mixin import UUIDMixin


class User(UUIDMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    ideas = relationship("Idea", back_populates="user",
                         cascade="all, delete-orphan")
