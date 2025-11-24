from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from jose import JWTError
from app.core.security import verify_token
from app.db.models.idea import Idea
from app.db.database import get_db
from app.db.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


async def get_token_from_header_or_cookie(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme)
) -> str:
    """
    Prioritize Authorization Header.
    If missing, fall back to Cookies.
    """
    if header_token:
        return header_token

    # Check Cookies
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    raise HTTPException(status_code=401, detail="Not authenticated")


async def get_current_user(
    token: str = Depends(get_token_from_header_or_cookie),
    db: AsyncSession = Depends(get_db)
) -> User:

    try:
        payload = verify_token(token, HTTPException(
            status_code=401, detail="Invalid token"))
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    user = await db.get(User, user_uuid)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


async def get_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user has verified email.
    Use this for write operations (create, update, delete).
    """
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email to perform this action. Check your inbox for the verification link.",
            headers={"X-Requires-Verification": "true"}
        )
    return current_user


async def get_idea_for_update(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user),
) -> Idea:
    """
    Dependency to get an Idea and verify ownership for updates.
    """
    from app.core.role_based_auth import require_admin
    query = (
        select(Idea)
        .options(selectinload(Idea.current_version))
        .where(Idea.id == idea_id)
    )

    result = await db.execute(query)
    idea = result.scalar_one_or_none()

    if not idea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Idea not found.",
        )

    # Check for admin role OR ownership
    if idea.author_id != current_user.id:
        await require_admin(current_user)

    return idea
