from pydantic import BaseModel, Field, computed_field
import math
from typing import Optional, List, Generic, TypeVar
from app.db.models.enum_json import VisibilityEnum, StageEnum
from datetime import datetime


T = TypeVar("T")


class IdeaCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    short_summary: str = Field(..., max_length=300)
    body_md: str = Field(...,
                         description="Full description in Markdown format")
    tags: Optional[List[str]] = Field(default=None)
    visibility: VisibilityEnum = Field(default=VisibilityEnum.public)
    stage: StageEnum = Field(default=StageEnum.seed)
    attachments: Optional[List[str]] = Field(default=None)


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    short_summary: Optional[str] = None
    body_md: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[VisibilityEnum] = None
    stage: Optional[StageEnum] = None


class IdeaVersionResponse(BaseModel):
    id: str
    title: str
    short_summary: str
    body_md: str
    attachments: Optional[List[str]]
    created_at: datetime

    class Config:
        from_attributes = True


class IdeaResponse(BaseModel):
    id: str
    author_id: str
    visibility: VisibilityEnum
    stage: StageEnum
    tags: Optional[List[str]]
    likes_count: int
    comments_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    # Embedded current version info
    current_version: Optional[IdeaVersionResponse]

    class Config:
        from_attributes = True


class PaginatedIdeasResponse(BaseModel, Generic[T]):
    total_count: int = Field(..., ge=0)
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
    items: List[T]

    @computed_field
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total_count / self.size) if self.size else 0

    class Config:
        from_attributes = True


class UpdateIdea(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    short_summary: str = Field(..., max_length=300)
    body_md: str = Field(...,
                         description="Full description in Markdown format")
    tags: Optional[List[str]] = Field(default=None, description="List of tags")
    visibility: Optional[VisibilityEnum] = Field(
        default=None, description="Public or private")
    stage: Optional[StageEnum] = Field(default=None, description="Idea stage")

    class Config:
        from_attributes = True
