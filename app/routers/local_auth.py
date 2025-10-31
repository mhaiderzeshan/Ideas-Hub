from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from app.schemas.user import UserCreate, UserResponse
from fastapi.responses import JSONResponse
from app.core.util import hashed_password, verify_hashed_password
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token_entry
)

IN_PRODUCTION = settings.ENVIRONMENT == "production"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

router = APIRouter(tags=["Local Authentication"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_pwd = hashed_password(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"message": "Signup successful. Please login."}
    )


@router.post("/login")
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    # Try to detect request type automatically
    content_type = request.headers.get("content-type", "")

    # JSON payload
    if "application/json" in content_type:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

    # Form data
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = str(form.get("email") or "")
        password = str(form.get("password") or "")

    # Invalid or missing content-type
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    # Validation check
    if not email or not password:
        raise HTTPException(
            status_code=400, detail="Email and password are required.")

    # Authenticate user
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_hashed_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token_entry(db, user.id)  # type: ignore

    # Set cookies (secure & HTTP-only)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=IN_PRODUCTION,
        samesite="lax",
        max_age=ACCESS_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IN_PRODUCTION,
        samesite="strict",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/auth",
    )

    return {"message": "Login successful"}
