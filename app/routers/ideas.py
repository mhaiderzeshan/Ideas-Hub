from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.schemas.idea_schemas import IdeaCreate, IdeaResponse, IdeaUpdate, PaginatedIdeasResponse
from sqlalchemy import select
from typing import Optional, List
from app.core.dependencies import get_current_user, get_verified_user
from app.db.models.idea import Idea, IdeaVersion
from app.db.models.user import User
import uuid
from app.crud.idea import get_idea_by_id, get_multi_ideas, create_new_idea_version, soft_delete_idea
from app.db.models.enum_json import StageEnum
from app.core.dependencies import get_idea_for_update


router = APIRouter(prefix="/ideas", tags=["Ideas"])


@router.post("/", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_idea(
    idea_data: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
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


@router.get("/", response_model=PaginatedIdeasResponse[IdeaResponse])
async def list_ideas(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100,
                      description="Number of items per page"),
    stage: Optional[StageEnum] = Query(None, description="Filter by stage"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    author_id: Optional[str] = Query(None, description="Filter by author ID"),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Get a paginated list of public ideas with filtering capabilities.
    """
    offset = (page - 1) * size
    ideas_list, total_count = await get_multi_ideas(
        db,
        offset=offset,
        limit=size,
        stage=stage,
        tags=tags,
        author_id=author_id
    )

    return PaginatedIdeasResponse(
        total_count=total_count,
        page=page,
        size=size,
        items=ideas_list,
    )


@router.put(
    "/{idea_id}",
    response_model=IdeaResponse,
    responses={
        403: {"description": "Permission denied"},
        404: {"description": "Idea not found"},
    },
)
async def update_idea_content(
    version_data: IdeaUpdate,
    db: AsyncSession = Depends(get_db),
    idea_to_update: Idea = Depends(get_idea_for_update),
):
    """
    Create a new version for an existing idea.

    This replaces the "current_version" of the idea with a new one.
    - **Permission**: Must be the author of the idea or an admin.
    """
    updated_idea = await create_new_idea_version(
        db=db, idea_to_update=idea_to_update, version_data=version_data
    )
    return updated_idea


@router.delete(
    "/{idea_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Permission denied"},
        404: {"description": "Idea not found"},
    },
)
async def delete_idea(
    db: AsyncSession = Depends(get_db),
    idea_to_delete: Idea = Depends(get_idea_for_update),
):
    """
    Soft delete an idea.

    This marks the idea as deleted but does not remove it from the database.
    - **Permission**: Must be the author of the idea or an admin.
    """
    await soft_delete_idea(db=db, idea_to_delete=idea_to_delete)

    return
