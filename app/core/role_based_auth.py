from fastapi import Depends, HTTPException, status
from app.db.models.user import User
from app.core.depedencies import get_current_user


def require_role(required_role: str):
    """
    Dependency function to require a specific user role

    Arguments:
    required_role - the role string (e.g., "admin", "user")

    return: dependency function
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}"
            )
        return current_user
    return dependency


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency function to require admin role"""
    return require_role("admin")(current_user)