from fastapi import APIRouter, Request, Depends, HTTPException
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime, timezone

from app.database import get_db
from app.models import User
from app.util import verify_token_hash
from app.models import RefreshToken
from app.auth import create_access_token, create_refresh_token_entry

router = APIRouter(tags=["auth"])

# Load OAuth config from .env
config = Config(".env")
oauth = OAuth(config)

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Redirect URI must match the one configured in Google console
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


@router.get("/login")
async def login(request: Request):
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(
            status_code=500, detail="Google client not configured")
    redirect_uri = request.url_for("auth_callback")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    client = oauth.create_client("google")
    if client is None:
        raise HTTPException(
            status_code=500, detail="OAuth client 'google' not configured")

    try:
        token = await client.authorize_access_token(request)
    except OAuthError as e:
        raise HTTPException(status_code=400, detail=f"OAuth Error: {str(e)}")

    userinfo = token.get("userinfo") or await client.parse_id_token(request, token)

    email = userinfo.get("email")
    name = userinfo.get("name") or email

    if not email:
        return {"error": "Email not provided by Google."}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    access = create_access_token({
        "sub": str(user.id),
        "role": user.role.value
    })
    refresh = create_refresh_token_entry(db, user.id)  # type: ignore

    # Create Response
    response = JSONResponse(content={"message": "Login successful"})

    # Store access token in a cookie
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=900
    )

    # Store refresh token
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=2592000  # 30 Days
    )

    return response


@router.post("/refresh")
def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=401, detail="No refresh token provided")

    # Find matching hashed token
    stored_tokens = db.query(RefreshToken).filter(
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc)
    ).all()

    valid_token = None
    for token in stored_tokens:
        if verify_token_hash(refresh_token, token.token):  # type: ignore
            valid_token = token
            break

    if not valid_token:
        raise HTTPException(
            status_code=401, detail="Invalid or expired refresh token")

    # Generate new access token
    access = create_access_token(
        {"sub": str(valid_token.user_id), "roles": ["user"]})

    response = JSONResponse(content={"message": "Token refreshed"})
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        samesite="lax",
        max_age=900
    )
    return response
