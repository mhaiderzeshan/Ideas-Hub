import secrets
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.user import User


class EmailVerificationService:

    @staticmethod
    async def create_verification_token(db: AsyncSession, user: User) -> str:
        """Create and store email verification token"""
        token = secrets.token_urlsafe(32)

        user.email_verification_token = token
        user.email_verification_token_expiry = datetime.utcnow() + timedelta(hours=24)

        await db.commit()
        await db.refresh(user)

        return token

    @staticmethod
    async def verify_email(db: AsyncSession, token: str) -> bool:
        """Verify email with token"""
        result = await db.execute(
            select(User).where(
                User.email_verification_token == token,
                User.email_verification_token_expiry > datetime.utcnow()
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            return False

        user.is_email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_token_expiry = None

        await db.commit()
        return True
