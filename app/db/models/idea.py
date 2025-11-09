from sqlalchemy import ForeignKey, DateTime, func, JSON, Enum, String, Integer, text, UniqueConstraint, Text, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.database import Base
from app.db.models.mixin import UUIDMixin
from app.db.models.enum_json import VisibilityEnum, StageEnum
from typing import Optional


class Idea(UUIDMixin, Base):
    __tablename__ = "ideas"

    current_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("idea_versions.id", name="fk_ideas_current_version_id", ondelete="SET NULL", use_alter=True),
        nullable=True
    )

    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_ideas_author_id", ondelete="CASCADE"),
        nullable=False
    )

    visibility: Mapped[VisibilityEnum] = mapped_column(
        Enum(VisibilityEnum), nullable=False, server_default=VisibilityEnum.public.value)
    stage: Mapped[StageEnum] = mapped_column(
        Enum(StageEnum), nullable=False, server_default=StageEnum.seed.value)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    likes_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False)
    comments_count: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships

    current_version = relationship(
        "IdeaVersion", 
        foreign_keys=[current_version_id], 
        post_update=True 
    )

    versions = relationship(
        "IdeaVersion", back_populates="idea", cascade="all, delete", foreign_keys="[IdeaVersion.idea_id]")
    stats = relationship("IdeaStat", back_populates="idea",
                         uselist=False, cascade="all, delete")
    author = relationship("User", back_populates="ideas")


class IdeaVersion(UUIDMixin, Base):
    __tablename__ = "idea_versions"
    __table_args__ = (UniqueConstraint(
        'idea_id', 'version_number', name='uq_idea_version_number'),)

    idea_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", name="fk_idea_versions_idea_id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_summary: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[list[str]]
                        ] = mapped_column(JSON, nullable=True)
    version_number: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    idea = relationship("Idea", back_populates="versions",
                        foreign_keys=[idea_id])


class IdeaStat(Base):
    __tablename__ = "idea_stats"

    idea_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", name="fk_idea_stats_idea_id", ondelete="CASCADE"),
        primary_key=True
    )

    upvotes: Mapped[int] = mapped_column(default=0)
    downvotes: Mapped[int] = mapped_column(default=0)
    comments: Mapped[int] = mapped_column(default=0)
    views: Mapped[int] = mapped_column(BigInteger, default=0)

    idea = relationship("Idea", back_populates="stats")
