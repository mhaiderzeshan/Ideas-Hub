import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base, engine
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user)
    created_at = Column(DateTime, server_default=sa.func.now())

    refresh_tokens = relationship("RefreshToken", back_populates="user")
#    ideas = relationship("Idea", back_populates="owner",
#                         cascade="save-update, merge")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(500), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=sa.func.now())

    user = relationship("User", back_populates="refresh_tokens")


"""class Idea(Base):
    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"),
                      nullable=False, index=True)
    created_at = Column(DateTime, server_default=sa.func.now())

    owner = relationship("User", back_populates="ideas")"""


Base.metadata.create_all(bind=engine)
