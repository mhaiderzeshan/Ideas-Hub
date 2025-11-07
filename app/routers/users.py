from fastapi import APIRouter, Depends
from app.db.models.user import User
from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user
from app.core.role_based_auth import require_admin


router = APIRouter(tags=["Users"])


@router.get("/me", responses={401: {"description": "Not authenticated"}}, response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user)):
    """
    Get the details of the currently authenticated user.
    """
    return current_user


@router.get("/admin", response_model=UserResponse)
async def read_admin_data(
    # The `require_admin` dependency runs, validates, and returns the admin user,
    # which is then injected into this parameter.
    admin_user: User = Depends(require_admin)
):
    """
    An example protected route that requires admin privileges.
    Returns the admin user's details upon successful authorization.
    """
    return admin_user
