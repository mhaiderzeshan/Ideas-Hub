from fastapi import APIRouter, Request, Depends, HTTPException, status
from app.models import User
from sqlalchemy.orm import Session
from app.database import get_db
from typing import Final
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

load_dotenv()

_secret = os.getenv("SECRET_KEY")
if _secret is None:
    raise ValueError("SECRET_KEY environment variable not set")

SECRET_KEY: Final[str] = _secret

_algorithm = os.getenv("ALGORITHM")
if _algorithm is None:
    raise ValueError("ALGORITHM environment variable not set")

ALGORITHM: Final[str] = _algorithm


router = APIRouter(tags=["User"])


async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # get user from DB
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/me", responses={401: {"description": "Not authenticated"}})
async def read_current_user(current_user: User = Depends(get_current_user_from_cookie)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }
