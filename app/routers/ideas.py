from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.schemas.post_idea import IdeaCreate, IdeaResponse, IdeaUpdate
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
from app.core.dependencies import get_current_user
from app.db.models.idea import Idea, IdeaVersion
from app.db.models.user import User
import uuid
from app.crud.idea import get_idea_by_id


router = APIRouter(prefix="/ideas", tags=["Ideas"])


@router.post("/", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_idea(
    idea_data: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    new_idea = Idea(
        id=str(uuid.uuid4()),
        author_id=current_user.id,
        tags=idea_data.tags or [],
        visibility=idea_data.visibility,
        stage=idea_data.stage,
    )
    db.add(new_idea)
    await db.flush()  # ensures new_idea.id is available

    new_idea_version = IdeaVersion(
        id=str(uuid.uuid4()),
        idea_id=new_idea.id,
        title=idea_data.title,
        short_summary=idea_data.short_summary,
        body_md=idea_data.body_md,
        attachments=idea_data.attachments or [],
        version_number=1,
    )
    db.add(new_idea_version)
    await db.flush()  # ensures new_idea_version.id is available

    new_idea.current_version_id = new_idea_version.id

    await db.commit()

    query = (
        select(Idea)
        .where(Idea.id == new_idea.id)
        .options(selectinload(Idea.current_version))
    )
    result = await db.execute(query)
    created_idea_with_version = result.scalar_one()

    return created_idea_with_version


@router.get("/{id}", response_model=IdeaResponse)
async def get_idea(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get a single idea by its ID.

    Returns the canonical idea data along with the full content of its current version.
    - Public ideas are visible to everyone.
    - Private ideas are only visible to their authors.
    """
    idea = await get_idea_by_id(
        db,
        idea_id=id,
        requesting_user=current_user)

    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Idea not found")

    return idea
