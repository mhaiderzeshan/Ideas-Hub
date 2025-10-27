from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
import os
from app.util import hash_token
from app.models import RefreshToken
from typing import cast

from app.database import get_db
from app.models import User
from app.auth import (
    create_access_token,
    create_refresh_token_entry,
    revoke_refresh_token,
    verify_refresh_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

config = Config(".env")
oauth = OAuth(config)

IN_PRODUCTION = os.getenv("ENVIRONMENT") == "production"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

ACCESS_COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login")
async def login(request: Request):
    """
    Redirects the user to Google's OAuth 2.0 consent screen.
    """
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="Google OAuth client not configured")

    redirect_uri = request.url_for("auth_callback")
    print("👉 Redirect URI being sent to Google:", redirect_uri)
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the callback from Google after user authorization.
    Finds or creates the user, and sets secure access and refresh tokens in cookies.
    """
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="OAuth client 'google' not configured")

    try:
        token_data = await client.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(
            status_code=401, detail=f"Authentication failed: {e.error}")

    userinfo = token_data.get("userinfo")
    if not userinfo:
        raise HTTPException(
            status_code=400, detail="Could not retrieve user info from token.")

    email = userinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=400, detail="Email not provided by identity provider.")

    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        user = User(
            email=email,
            name=userinfo.get("name") or email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    response_data = {
        "message": "Login successful",
        "user": {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role.value},
    }
    response = JSONResponse(content=response_data)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value})
    refresh_token = create_refresh_token_entry(db, user.id)  # type: ignore

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


@router.post("/refresh")
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
        refresh_token_id = cast(int, payload["refresh_token_id"])
    except HTTPException:
        response.delete_cookie("refresh_token")
        response.delete_cookie("access_token")
        raise credentials_exception
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


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Logs the user out by revoking their refresh token and deleting session cookies.

    This performs two actions:
    1. Invalidates the refresh token on the server-side by marking it as 'revoked'.
    2. Instructs the client's browser to delete the access and refresh token cookies.
    """
    refresh_token_value = request.cookies.get("refresh_token")

    if refresh_token_value:
        try:
            hashed_token = hash_token(refresh_token_value)

            # Find the corresponding token in the database
            token_record = (
                db.query(RefreshToken)
                .filter(RefreshToken.token == hashed_token, RefreshToken.revoked.is_(False))
                .one_or_none()
            )

            if token_record:
                setattr(token_record, "revoked", True)
                db.commit()
        except Exception:
            # logger.error("Error revoking refresh token during logout.")
            pass

    response_data = {"message": "Logout successful"}
    final_response = JSONResponse(content=response_data)

    final_response.delete_cookie("access_token")
    final_response.delete_cookie("refresh_token", path="/auth")

    for header in final_response.headers.raw:
        if header[0] == b"set-cookie":
            response.raw_headers.append(header)

    return response_data
