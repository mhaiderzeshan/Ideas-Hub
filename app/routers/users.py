from fastapi import APIRouter, Request, Depends, HTTPException, status
from app.db.models.user import User
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models.user import User
from jose import JWTError, jwt
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY.get_secret_value()
ALGORITHM = settings.ALGORITHM


router = APIRouter(tags=["Users"])


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
