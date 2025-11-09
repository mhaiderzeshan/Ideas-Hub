from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.models.idea import Idea
from sqlalchemy.orm import selectinload 
from sqlalchemy import select
from app.db.models.enum_json import VisibilityEnum
from app.db.models.user import User



async def get_idea_by_id(
        db: AsyncSession,
        *,
        idea_id: str,
        requesting_user: Optional[User]) -> Optional[Idea]:
    
    query = (
        select(Idea)
        .where(Idea.id == idea_id)
        .options(selectinload(Idea.current_version))
    )

    result = await db.execute(query)
    idea = result.scalar_one_or_none()

    if not idea:
        pass

    if idea.visibility == VisibilityEnum.public:
        return idea
    
    if idea.visibility == VisibilityEnum.private:
        if requesting_user and idea.author_id == requesting_user.id:
            return idea
        
    return None