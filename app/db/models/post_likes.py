from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.database import Base


class PostLike(Base):
    __tablename__ = "post_likes"
    __table_args__ = (UniqueConstraint(
        'post_id', 'user_id', name="uq_post_likes_post_id_user_id"),)

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)

    post_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("ideas.id", name="fk_post_likes_post_id",
                   ondelete="CASCADE"),
        nullable=False
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", name="fk_post_likes_user_id",
                   ondelete="CASCADE"),
        nullable=False
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    post = relationship("Idea", back_populates="likes")
    user = relationship("User", back_populates="likes")
