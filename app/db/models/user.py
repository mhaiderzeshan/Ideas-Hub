from sqlalchemy import String, Integer, Enum, DateTime, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from app.db.database import Base
from app.db.models.enum_json import UserRole
from app.db.models.mixin import UUIDMixin


class User(UUIDMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)

    # Email verification fields
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True)
    email_verification_token_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True)

    # Password reset fields
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True)
    reset_token_expires: Mapped[Optional[datetime]
                                ] = mapped_column(DateTime, nullable=True)
    reset_attempts: Mapped[int] = mapped_column(Integer, default=0)

    # Security tracking
    password_changed_at: Mapped[Optional[datetime]
                                ] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[Optional[datetime]
                          ] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_login_at: Mapped[Optional[datetime]
                                 ] = mapped_column(DateTime, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now())

    auth_provider: Mapped[Optional[str]] = mapped_column(
        String(50), default="local", nullable=True)

    def __init__(self, email: str, name: str | None = None, **kw):
        super().__init__(**kw)
        self.email = email
        self.name = name or email

    refresh_tokens = relationship("RefreshToken", back_populates="user")
    ideas = relationship("Idea", back_populates="author",
                         cascade="all, delete-orphan")
