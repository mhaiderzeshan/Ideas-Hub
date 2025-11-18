import asyncio
from fastapi import APIRouter, Request, Depends, HTTPException, Response, status
from sqlalchemy import select
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth, OAuthError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import cast

# Local application imports
from app.db.database import get_db
from app.db.models.user import User
from app.db.models.token import RefreshToken
from app.core.util import hash_token
from app.core.rate_limiter import rate_limit
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token_entry,
    revoke_refresh_token,
    verify_refresh_token
)

router = APIRouter(prefix="/auth", tags=["Google Authentication"])
oauth = OAuth()

# --- Configuration Constants ---
IN_PRODUCTION = settings.ENVIRONMENT == "production"
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET.get_secret_value()

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

# --- OAuth Client Registration ---
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def login(request: Request):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="Google OAuth client not configured")
    redirect_uri = request.url_for("auth_callback")
    print(f"DEBUG: Generating authorize redirect for URI: {redirect_uri}")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="OAuth client 'google' not configured")

    try:
        token_data = await client.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(
            status_code=401, detail=f"Authentication failed: {e.error}")

    id_token_value = token_data.get("id_token")
    if not id_token_value:
        raise HTTPException(
            status_code=400, detail="No ID token returned by Google")

    try:
        id_info = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            id_token_value, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid ID token: {str(e)}")

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=400, detail="Email not found in ID token")

    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=email, name=id_info.get("name") or email)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # --- Create Tokens ---
    refresh_token = await create_refresh_token_entry(db, user.id)
    access_token = create_access_token(data={"sub": str(user.id)})

    redirect_url = settings.FRONTEND_URL + "/dashboard"
    response = RedirectResponse(url=redirect_url)

    # Set the access and refresh tokens in secure, HTTP-only cookies
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # Prevents JS access
        max_age=ACCESS_COOKIE_MAX_AGE,
        samesite="none",
        secure=IN_PRODUCTION  # Use True in production
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # Prevents JS access
        max_age=REFRESH_COOKIE_MAX_AGE,
        samesite="none",
        secure=IN_PRODUCTION  # Use True in production
    )

    return response


@router.post("/refresh", dependencies=[Depends(rate_limit)])
async def refresh_access_token(request: Request, response: Response, db: AsyncSession = Depends(get_db)):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    incoming_refresh_token = request.cookies.get("refresh_token")
    if not incoming_refresh_token:
        raise credentials_exception

    try:
        payload = await verify_refresh_token(incoming_refresh_token, db, credentials_exception)
        user_id = payload["user_id"]
        refresh_token_id = cast(int, payload.get("id"))
    except HTTPException:
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        raise credentials_exception

    await revoke_refresh_token(db, refresh_token_id)

    user = await db.get(User, user_id)
    if not user:
        raise credentials_exception

    new_access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = await create_refresh_token_entry(db, user.id)

    response.set_cookie(
        key="access_token",
        value=f"Bearer {new_access_token}",
        httponly=True,
        max_age=ACCESS_COOKIE_MAX_AGE,
        samesite="lax",
        secure=IN_PRODUCTION,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        max_age=REFRESH_COOKIE_MAX_AGE,
        samesite="lax",
        secure=IN_PRODUCTION,
    )

    return {"message": "Token refreshed successfully"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_token_value = request.cookies.get("refresh_token")

    if refresh_token_value:
        try:
            hashed_token = hash_token(refresh_token_value)
            query = select(RefreshToken).where(
                RefreshToken.token == hashed_token,
                RefreshToken.revoked.is_(False)
            )
            result = await db.execute(query)
            token_record = result.scalar_one_or_none()

            if token_record:
                setattr(token_record, "revoked", True)
                await db.commit()
        except Exception:
            pass  # Fails silently if token is invalid or already revoked

    response.delete_cookie(
        key="access_token", httponly=True, samesite="lax", secure=IN_PRODUCTION
    )
    response.delete_cookie(
        key="refresh_token", httponly=True, samesite="lax", secure=IN_PRODUCTION
    )

    return {"message": "You have been successfully logged out."}
