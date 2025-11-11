from fastapi import Request, HTTPException, status
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import secrets
import uuid

from app.core.util import hash_token
from app.core.config import settings


SECRET_KEY = settings.SECRET_KEY.get_secret_value()
ALGORITHM = settings.ALGORITHM
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"iat": now, "exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise credentials_exception


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def get_access_token_from_cookie(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return token


async def verify_refresh_token(refresh_token: str, db: AsyncSession, credentials_exception):
    from app.db.models.token import RefreshToken
    hashed = hash_token(refresh_token)

    query = select(RefreshToken).where(
        RefreshToken.token == hashed,
        RefreshToken.revoked == False
    )
    result = await db.execute(query)
    db_refresh_token = result.scalar_one_or_none()

    if not db_refresh_token:
        raise credentials_exception

    if datetime.now(timezone.utc) > db_refresh_token.expires_at:
        await db.delete(db_refresh_token)
        await db.commit()
        raise credentials_exception

    return {
        "user_id": db_refresh_token.user_id,
        "id": db_refresh_token.id,
    }


async def create_refresh_token_entry(db: AsyncSession, user_id: int) -> str:
    from app.db.models.token import RefreshToken
    # Use cryptographically secure token generation
    raw_refresh_token = create_refresh_token()
    hashed_token = hash_token(raw_refresh_token)

    expires_at = datetime.now(timezone.utc) + \
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    new_entry = RefreshToken(
        user_id=user_id,
        token=hashed_token,
        jti=str(uuid.uuid4()),
        expires_at=expires_at,
    )
    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    # Return the raw, un-hashed token to the user
    return raw_refresh_token


async def revoke_refresh_token(db: AsyncSession, refresh_token_id: int):
    from app.db.models.token import RefreshToken

    token = await db.get(RefreshToken, refresh_token_id)

    if token and not token.revoked:
        setattr(token, "revoked", True)
        await db.commit()
