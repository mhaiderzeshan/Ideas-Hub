from fastapi import FastAPI
import app.db.models
from app.db.database import engine, Base
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings


Base.metadata.create_all(bind=engine)

SECRET_KEY = settings.SECRET_KEY.get_secret_value()

from app.routers.local_auth import router as local_auth_router
from app.routers.auth_google import router as oauth_router
from app.routers.users import router as user_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(local_auth_router)
app.include_router(oauth_router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.include_router(user_router)



@app.get("/")
async def root():
    return {"message": "Hello World"}
