# app/main.py
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import cloudinary

from app.db.database import engine, Base
from app.core.config import settings
from app.routers.local_auth import router as local_auth_router
from app.routers.auth_google import router as oauth_router
from app.routers.users import router as user_router
from app.routers.ideas import router as idea_router
from app.routers.upload import router as upload_router
from app.routers.likes import router as likes_router
from app.routers.auth import router as auth_router
from app.routers.email_verification import router as email_verification_router


async def create_db_and_tables():
    """
    Asynchronously creates all database tables defined in the Base metadata.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    The lifespan context manager for the FastAPI application.
    """
    await create_db_and_tables()
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET.get_secret_value(),
        cloudinary_folder=settings.CLOUDINARY_FOLDER
    )

    yield

SECRET_KEY = settings.SECRET_KEY.get_secret_value()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=settings.ENVIRONMENT == "production",
    same_site='none'
)


app.include_router(local_auth_router)
app.include_router(email_verification_router)
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(user_router)
app.include_router(idea_router)
app.include_router(upload_router)
app.include_router(likes_router)


@app.get("/")
async def root():
    return {"message": "Hello Ideas Hub!"}
