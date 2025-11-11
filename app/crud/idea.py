import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Tuple
from app.db.models.idea import Idea, IdeaVersion
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, or_
from app.db.models.enum_json import VisibilityEnum, StageEnum
from app.schemas.idea_schemas import IdeaUpdate
from app.db.models.user import User


async def get_idea_by_id(
        db: AsyncSession,
        *,
        idea_id: str,
        requesting_user: Optional[User]) -> Optional[Idea]:

    query = (
        select(Idea)
        .where(Idea.id == idea_id)
        .where(Idea.is_deleted.is_(False))
        .options(selectinload(Idea.current_version))
    )

    result = await db.execute(query)
    idea = result.scalar_one_or_none()

    if idea is None:
        return None

    if idea.visibility == VisibilityEnum.public:
        return idea

    if idea.visibility == VisibilityEnum.private:
        if requesting_user and idea.author_id == requesting_user.id:
            return idea

    return None


async def get_multi_ideas(
        db: AsyncSession,
        *,
        offset: int = 0,
        limit: int = 10,
        stage: Optional[StageEnum] = None,
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None
) -> Tuple[List[Idea], int]:
    """
    Fetches a paginated, filtered, and sorted list of ideas.
    Only returns PUBLIC ideas.

    Returns a tuple of (list_of_ideas, total_item_count).
    """
    query = select(Idea).options(selectinload(Idea.current_version))

    query = query.where(Idea.is_deleted.is_(False))

    query = query.where(Idea.visibility == VisibilityEnum.public)

    if stage:
        query = query.where(Idea.stage == stage)

    if author_id:
        query = query.where(Idea.author_id == author_id)

    if tags:
        query = query.where(or_(*[Idea.tags.contains(tag) for tag in tags]))

    count_query = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_query)).scalar_one()

    paginated_query = query.offset(offset).limit(limit)

    result = await db.execute(paginated_query)
    items = result.scalars().all()

    return list(items), total_items


async def create_new_idea_version(
    db: AsyncSession,
    *,
    idea_to_update: Idea,
    version_data: IdeaUpdate,
) -> Idea:
    """
    Creates a new IdeaVersion, updates the parent Idea's current_version_id,
    and commits the transaction.
    Inherits tags, visibility, and stage from current version if not provided.
    """

    # Find the highest existing version number
    max_version_query = select(func.max(IdeaVersion.version_number)).where(
        IdeaVersion.idea_id == idea_to_update.id
    )
    max_version_result = await db.execute(max_version_query)
    current_max_version = max_version_result.scalar_one_or_none() or 0

    # Determine values for optional fields
    tags: list[str] = version_data.tags if version_data.tags is not None else (
        idea_to_update.tags or [])
    visibility: VisibilityEnum = version_data.visibility if version_data.visibility is not None else idea_to_update.visibility
    stage: StageEnum = version_data.stage if version_data.stage is not None else idea_to_update.stage

    # Create new version
    new_version = IdeaVersion(
        id=str(uuid.uuid4()),
        idea_id=idea_to_update.id,
        title=version_data.title,
        short_summary=version_data.short_summary,
        body_md=version_data.body_md,
        version_number=current_max_version + 1
    )

    # Add and flush to get ID
    db.add(new_version)
    await db.flush()

    # Update parent idea
    idea_to_update.current_version_id = new_version.id
    idea_to_update.tags = tags
    idea_to_update.visibility = visibility
    idea_to_update.stage = stage

    # Commit transaction
    await db.commit()

    # Refresh idea to load the new relationship
    await db.refresh(new_version)
    await db.refresh(idea_to_update)

    return idea_to_update


async def soft_delete_idea(db: AsyncSession, *, idea_to_delete: Idea) -> None:
    """
    Marks an idea as deleted (soft delete).
    """
    # Set the flag to True
    setattr(idea_to_delete, "is_deleted", True)

    await db.commit()
