from fastapi import APIRouter, Depends
from app.db.models.user import User
from app.db.models.user import User
from app.core.config import settings
from app.schemas.user import UserResponse
from app.core.role_based_auth import require_admin
from app.core.depedencies import get_current_user


SECRET_KEY = settings.SECRET_KEY.get_secret_value()
ALGORITHM = settings.ALGORITHM


router = APIRouter(tags=["Users"])


@router.get("/me", responses={401: {"description": "Not authenticated"}}, response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin", dependencies=[Depends(require_admin)])
async def read_admin_user(current_user: User = Depends(get_current_user)):
    return current_user
