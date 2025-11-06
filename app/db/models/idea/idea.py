from sqlalchemy import ForeignKey, DateTime, func, JSON, Enum, String, Integer, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.database import Base
from app.db.models.mixin import UUIDMixin
from app.db.models.enum_json import VisibilityEnum, StageEnum
from typing import Optional


class Idea(UUIDMixin, Base):
    __tablename__ = "ideas"

    current_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("idea_versions.id", ondelete="SET NULL"),
        nullable=True
    )

    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    visibility: Mapped[VisibilityEnum] = mapped_column(
        Enum(VisibilityEnum), nullable=False, server_default=VisibilityEnum.public.value)
    stage: Mapped[StageEnum] = mapped_column(Enum(StageEnum), nullable=False, server_default=StageEnum.seed.value)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    likes_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=False)

    # Relationships
    versions = relationship(
        "IdeaVersion", back_populates="idea", cascade="all, delete")
    stats = relationship("IdeaStat", back_populates="idea",
                         uselist=False, cascade="all, delete")
    user = relationship("User", back_populates="ideas")
