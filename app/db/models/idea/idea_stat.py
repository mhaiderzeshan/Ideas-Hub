from sqlalchemy import BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.database import Base
from sqlalchemy import ForeignKey, String


class IdeaStat(Base):
    __tablename__ = "idea_stats"

    idea_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", ondelete="CASCADE"),
        primary_key=True
    )

    upvotes: Mapped[int] = mapped_column(default=0)
    downvotes: Mapped[int] = mapped_column(default=0)
    comments: Mapped[int] = mapped_column(default=0)
    views: Mapped[int] = mapped_column(BigInteger, default=0)

    idea = relationship("Idea", back_populates="stats")
