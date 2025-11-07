from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.schemas.post_idea import IdeaCreate, IdeaResponse
from app.core.dependencies import get_current_user
from app.db.models.idea import Idea, IdeaVersion
from app.db.models.user import User
import uuid

router = APIRouter(tags=["Ideas"])


@router.post("/", response_model=IdeaResponse, status_code=status.HTTP_201_CREATED)
async def create_idea(
    idea_data: IdeaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create the main idea object
    new_idea = Idea(
        id=str(uuid.uuid4()),
        author_id=current_user.id,
        tags=idea_data.tags or [],
        visibility=idea_data.visibility,
        stage=idea_data.stage,
    )
    db.add(new_idea)

    # Create the initial version of the idea
    new_idea_version = IdeaVersion(
        id=str(uuid.uuid4()),
        idea_id=new_idea.id,
        title=idea_data.title,
        short_summary=idea_data.short_summary,
        body_md=idea_data.body_md,
        attachments=idea_data.attachments or [],
    )
    db.add(new_idea_version)

    # Link the idea to its initial version
    new_idea.current_version_id = new_idea_version.id

    await db.commit()

    await db.refresh(new_idea)

    return new_idea
