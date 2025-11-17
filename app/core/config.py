from pydantic_settings import BaseSettings
from pydantic import SecretStr, EmailStr


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        extra = "ignore"

    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str
    DB_PORT: int
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
    REDIS_URL: str

    BREVO_API_KEY: SecretStr
    EMAIL_FROM: EmailStr
    EMAIL_FROM_NAME: str = "Ideas Hub"
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_TIMEOUT: int = 30
    MAX_RETRIES: int = 3


settings = Settings()  # type: ignore
