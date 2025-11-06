import uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from app.db.database import Base


class UUIDMixin:
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
