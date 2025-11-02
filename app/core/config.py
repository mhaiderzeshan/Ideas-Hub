from pydantic_settings import BaseSettings
from pydantic import SecretStr


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        extra = "ignore"

    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    ENVIRONMENT: str = "production"
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: SecretStr
    GOOGLE_REDIRECT_URI: str
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()  # type: ignore
