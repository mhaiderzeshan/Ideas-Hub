from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Final
import secrets
import os
from app.models import RefreshToken

from dotenv import load_dotenv

load_dotenv()


_secret = os.getenv("SECRET_KEY")
if _secret is None:
    raise ValueError("SECRET_KEY environment variable not set")

SECRET_KEY: Final[str] = _secret

_algorithm = os.getenv("ALGORITHM")
if _algorithm is None:
    raise ValueError("ALGORITHM environment variable not set")

ALGORITHM: Final[str] = _algorithm

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT token for access.

    Args:
        data: the payload data to include in the token (e.g. {"sub": user_id, "role": "admin"})
        expires_delta: optional timedelta to override default expiry

    Returns:
        A JWT token string.
    """
    to_encode = data.copy()

    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": now})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception) -> str:
    """
    Verify the JWT token and return the subject.

    Args:
        token: JWT string to verify
        credentials_exception: exception to raise on validation failure

    Returns:
        The token subject as a string (currently user id serialized as a string).

    Note: The token `sub` claim is the user's id (string). Do not assume `sub` is
    an email address; if consumers need the user's email, include it as a
    separate claim and resolve server-side when necessary.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None or not isinstance(username, str):
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


def create_refresh_token():
    """
    Create a secure refresh token using secrets module

    return: str of the refresh token
    """
    return secrets.token_urlsafe(32)


def verify_refresh_token(refresh_token: str, db, credentials_exception) -> dict:
    """
    Verify the refresh token against the database

    Argument:
    refresh_token - the refresh token to verify
    db - database session
    credentials_exception - exception to raise if invalid

    return: dict with user_id and refresh_token_id
    """

    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if not db_refresh_token:
        raise credentials_exception

    # Check if token is expired
    if datetime.utcnow() > db_refresh_token.expires_at:
        # Delete expired token
        db.delete(db_refresh_token)
        db.commit()
        raise credentials_exception

    return {
        "user_id": db_refresh_token.user_id,
        "refresh_token_id": db_refresh_token.id
    }


def create_refresh_token_entry(db, user_id: int) -> str:
    """
    Create a new refresh token entry in the database

    Arguments:
    db - database session
    user_id - the user id for whom to create the token

    return: the refresh token string
    """

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.expires_at < datetime.utcnow()
    ).delete()
    db.commit()

    # Generate new refresh token
    refresh_token = create_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    new_refresh_token = RefreshToken(
        token=refresh_token,
        user_id=user_id,
        expires_at=expires_at
    )

    db.add(new_refresh_token)
    db.commit()
    db.refresh(new_refresh_token)

    return refresh_token


def revoke_refresh_token(db, refresh_token_id: int):
    """
    Revoke a refresh token by deleting it from the database

    Arguments:
    db - database session
    refresh_token_id - the id of the refresh token to revoke
    """
    db.query(RefreshToken).filter(RefreshToken.id == refresh_token_id).delete()
    db.commit()
