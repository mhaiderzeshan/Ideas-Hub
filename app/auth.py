from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Final
from sqlalchemy.orm import Session
from app.util import hash_token
from datetime import datetime, timezone, timedelta
import secrets
import uuid
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

    to_encode.update({
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4())
    })

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


def verify_refresh_token(refresh_token: str, db: Session, credentials_exception):
    """Verify hashed token and expiry."""
    hashed = hash_token(refresh_token)

    db_refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == hashed,
        RefreshToken.revoked == False
    ).first()

    if not db_refresh_token:
        raise credentials_exception

    if (datetime.now(timezone.utc) > db_refresh_token.expires_at).scalar():
        db.delete(db_refresh_token)
        db.commit()
        raise credentials_exception

    return {
        "user_id": db_refresh_token.user_id,
        "refresh_token_id": db_refresh_token.id,
    }


def create_refresh_token_entry(db: Session, user_id: int):
    # Generate a unique token (string)
    refresh_token = str(uuid.uuid4())

    # Hash it before storing
    hashed = hash_token(refresh_token)

    expires_at = datetime.now(timezone.utc) + \
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    new_entry = RefreshToken(
        user_id=user_id,
        token=hashed,
        jti=str(uuid.uuid4()),  # unique ID for the token
        expires_at=expires_at,
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    return refresh_token


def revoke_refresh_token(db: Session, refresh_token_id: int):
    """Mark a refresh token as revoked."""
    token = db.query(RefreshToken).filter(
        RefreshToken.id == refresh_token_id).first()
    if token:
        # use setattr to avoid static type check errors assigning a Literal to a Column-typed attribute
        setattr(token, "revoked", True)
        db.commit()
