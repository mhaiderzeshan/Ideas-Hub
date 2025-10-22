from fastapi import APIRouter, Request, Depends, HTTPException
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config
from sqlalchemy.orm import Session
import os

from app.database import get_db
from app.models import User
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

    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token_entry(db, user.id)  # type: ignore
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer"
    }
