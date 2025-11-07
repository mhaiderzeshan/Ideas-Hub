from fastapi import Depends, HTTPException, status
from app.db.models.user import User
from app.core.dependencies import get_current_user


def require_role(required_role: str):
    """
    A dependency factory that returns an async dependency to check a user's role.

    Arguments:
    - required_role: The role string (e.g., "admin", "user") to check for.

    Returns:
    - An async dependency function.
    """
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not hasattr(current_user, 'role') or current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    
    return dependency

require_admin = require_role("admin")
