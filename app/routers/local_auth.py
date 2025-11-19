from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, BackgroundTasks
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate
from app.services.email_verification import EmailVerificationService
from app.services.email_service import EmailService
from app.core.util import hashed_password, verify_hashed_password
from app.core.rate_limiter import rate_limit
from app.crud.auth import auth_service
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token_entry,
)

IN_PRODUCTION = settings.ENVIRONMENT == "production"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Local Authentication"])


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit)])
async def create_user(user: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    query = select(User).where(User.email == user.email)
    result = await db.execute(query)
    db_user = result.scalar_one_or_none()

    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_pwd = hashed_password(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hashed_pwd,
        auth_provider="local",
        is_email_verified=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = await EmailVerificationService.create_verification_token(db, new_user)

    # Send verification email in background
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    background_tasks.add_task(
        EmailService.send_verification_email,
        new_user.email,
        new_user.name,
        verification_url
    )

    return {"message": "Signup successful. Please check your email to verify your account."}


@router.post("/login", dependencies=[Depends(rate_limit)])
async def login(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    if "application/json" in content_type:
        data = await request.json()
        email = data.get("email")
        password = data.get("password")

    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form_data = await request.form()
        email = form_data.get("email")
        password = form_data.get("password")

    else:
        raise HTTPException(
            status_code=415, detail="Unsupported content type. Use application/json or application/x-www-form-urlencoded.")

    if not email or not password:
        raise HTTPException(
            status_code=400, detail="Email and password are required.")

     # USE THE AUTH SERVICE instead of duplicating logic
    user = await auth_service.authenticate_user(email, password, db)

    if not user:
        # Check if account is locked
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        check_user = result.scalar_one_or_none()

        if check_user and check_user.failed_login_attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account temporarily locked due to multiple failed login attempts. Please try again in 30 minutes or reset your password."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    # Check if email is verified (optional)
    if not user.is_email_verified:
        # You can still allow login but with limited access
        logger.warning(f"Unverified email login for user {user.id}")

    refresh_token = await create_refresh_token_entry(db, user.id)

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IN_PRODUCTION,
        samesite="none",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/auth",
    )

    return {
        "message": "Login successful",
        "email_verified": user.is_email_verified
    }
