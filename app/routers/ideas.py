from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.schemas.idea_schemas import IdeaCreate, IdeaResponse, IdeaUpdate, PaginatedIdeasResponse
from sqlalchemy import select
from typing import Optional, List
from app.core.permissions import get_idea_permissions
from app.core.dependencies import get_current_user, get_verified_user
from app.db.models.idea import Idea, IdeaVersion
from app.db.models.user import User
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
    """
    Create a new idea along with its initial version."""

    try:
        # Create the new idea and its initial version
        new_idea = Idea(
            author_id=current_user.id,
            tags=idea_data.tags or [],
            visibility=idea_data.visibility,
            stage=idea_data.stage,
        )
        db.add(new_idea)
        await db.flush()  # ensures new_idea.id is available

        new_idea_version = IdeaVersion(
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
            .options(
                selectinload(Idea.current_version),
                selectinload(Idea.author)
            )
        )

        result = await db.execute(query)
        final_idea = result.scalar_one()

        return final_idea

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create idea"
        ) from e


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

    permissions = get_idea_permissions(idea, current_user)

    response = IdeaResponse.model_validate(idea)

    response.can_edit = permissions["can_edit"]
    response.can_delete = permissions["can_delete"]

    return response


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

    processed_items = []
    for idea in ideas_list:
        # Calculate permissions for this specific idea
        permissions = get_idea_permissions(idea, current_user)

        # Convert to Pydantic model
        idea_response = IdeaResponse.model_validate(idea)

        # Inject flags
        idea_response.can_edit = permissions["can_edit"]
        idea_response.can_delete = permissions["can_delete"]

        processed_items.append(idea_response)

    return PaginatedIdeasResponse(
        total_count=total_count,
        page=page,
        size=size,
        items=processed_items,
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
    current_user: User = Depends(get_verified_user)
):
    """
    Create a new version for an existing idea.

    This replaces the "current_version" of the idea with a new one.
    - **Permission**: Must be the author of the idea or an admin.
    """
    updated_idea = await create_new_idea_version(
        db=db, idea_to_update=idea_to_update, version_data=version_data
    )

    permissions = get_idea_permissions(updated_idea, current_user)

    response = IdeaResponse.model_validate(updated_idea)

    response.can_edit = permissions["can_edit"]
    response.can_delete = permissions["can_delete"]

    return response


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
