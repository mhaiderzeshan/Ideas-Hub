from sqlalchemy import ForeignKey, DateTime, func, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.database import Base
from app.db.models.mixin import UUIDMixin
from typing import Optional


class IdeaVersion(UUIDMixin, Base):
    __tablename__ = "idea_versions"
    __table_args__ = (UniqueConstraint('idea_id', 'version_number', name='uq_idea_version_number'),)

    idea_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_summary: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)
    version_number: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    idea = relationship("Idea", back_populates="versions")
