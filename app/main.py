from fastapi import FastAPI
from app.routes.oauth import router as oauth_router
from starlette.middleware.sessions import SessionMiddleware
from fastapi.security import OAuth2PasswordBearer, HTTPBearer
from starlette.config import Config

config = Config(".env")
SECRET_KEY = config("SECRET_KEY", cast=str)


app = FastAPI()

app.include_router(oauth_router)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.get("/")
async def root():
    return {"message": "Hello World"}
