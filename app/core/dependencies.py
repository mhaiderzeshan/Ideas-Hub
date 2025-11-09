from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from jose import JWTError
from app.core.security import get_access_token_from_cookie, verify_token
from app.db.database import get_db
from app.db.models.user import User


async def get_current_user(
    token: str = Depends(get_access_token_from_cookie),
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

    user = await db.get(User, UUID(user_id))

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user
