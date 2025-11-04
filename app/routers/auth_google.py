from fastapi import APIRouter, Request, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.util import hash_token
from app.db.models.token import RefreshToken
from typing import cast
from app.core.rate_limiter import rate_limit
from app.core.config import settings

from app.db.database import get_db
from app.db.models.user import User
from app.core.security import (
    create_access_token,
    create_refresh_token_entry,
    revoke_refresh_token,
    verify_refresh_token
)

router = APIRouter(prefix="/auth", tags=["Google Authentication"])

oauth = OAuth()

IN_PRODUCTION = settings.ENVIRONMENT == "production"
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET.get_secret_value()

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def login(request: Request):
    """
    Redirects the user to Google's OAuth 2.0 consent screen.
    """
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="Google OAuth client not configured")

    redirect_uri = request.url_for("auth_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="OAuth client 'google' not configured")

    try:
        token_data = await client.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(
            status_code=401, detail=f"Authentication failed: {e.error}")

    # Verify ID token
    id_token_value = token_data.get("id_token")
    if not id_token_value:
        raise HTTPException(
            status_code=400, detail="No ID token returned by Google")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_value, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Invalid ID token: {str(e)}")

    # Extract verified user info
    email = id_info.get("email")
    name = id_info.get("name")

    if not email:
        raise HTTPException(
            status_code=400, detail="Email not found in ID token")

    # Find or create user in DB
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        user = User(email=email, name=name or email)
        db.add(user)
        db.commit()
        db.refresh(user)

    # Create JWT access + refresh tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token_entry(db, user.id)  # type: ignore

    # Set them in cookies
    response_data = {"message": "Login successful", "user": {
        "id": str(user.id), "email": user.email, "name": user.name}}
    response = JSONResponse(content=response_data)

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

    return response


@router.post("/refresh", dependencies=[Depends(rate_limit)])
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    incoming_refresh_token = request.cookies.get("refresh_token")
    if not incoming_refresh_token:
        raise credentials_exception
    try:
        payload = verify_refresh_token(
            incoming_refresh_token, db, credentials_exception)
        user_id = payload["user_id"]
        refresh_token_id = cast(int, payload.get("id"))
    except HTTPException:
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        raise credentials_exception

    revoke_refresh_token(db, refresh_token_id)

    user = db.get(User, user_id)
    if not user:
        raise credentials_exception

    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value})
    new_refresh_token = create_refresh_token_entry(db, user.id)  # type: ignore

    # Set the new tokens in cookies
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=IN_PRODUCTION,
        samesite="lax",
        max_age=ACCESS_COOKIE_MAX_AGE,
    )
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=IN_PRODUCTION,
        samesite="strict",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/auth",
    )

    return {"message": "Token refreshed successfully"}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(request: Request, db: Session = Depends(get_db)):
    """
    Logs the user out.

    This endpoint is idempotent. It ensures the client is in a logged-out state
    by performing two actions:
    1. If a valid refresh token is provided, it's revoked on the server-side.
    2. It instructs the client's browser to delete the session cookies, regardless
       of whether a valid session existed.
    """
    refresh_token_value = request.cookies.get("refresh_token")

    # If a token exists, attempt to revoke it on the server.
    # We don't raise an error if the token is invalid or not found, as the
    # end goal is simply to ensure the session is terminated.
    if refresh_token_value:
        try:
            hashed_token = hash_token(refresh_token_value)
            token_record = db.query(RefreshToken).filter(
                RefreshToken.token == hashed_token,
                RefreshToken.revoked.is_(False)
            ).one_or_none()

            if token_record:
                setattr(token_record, "revoked", True)
                db.commit()
        except Exception as e:
            # This is a place for logging, as an unexpected error here could
            # indicate a problem. But we don't let it stop the logout process.
            # logger.error(f"Error during token revocation on logout: {e}")
            pass

    # ALWAYS instruct the browser to clear cookies. This cleans up stale cookies
    # and ensures the client-side state is clean.
    response = JSONResponse(
        content={"message": "You have been successfully logged out."})
    response.delete_cookie(
        "access_token", path="/", secure=IN_PRODUCTION, httponly=True, samesite="lax"
    )
    response.delete_cookie(
        "refresh_token", path="/auth", secure=IN_PRODUCTION, httponly=True, samesite="lax"
    )

    return response
