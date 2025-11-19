import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.db.models.user import User
from app.core.email import get_email_service
from app.core.util import (
    hash_token,
    async_hashed_password,
    async_verify_hashed_password
)

# Configure logger
logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication and password management"""

    # Configuration constants
    RESET_TOKEN_LENGTH = 32
    RESET_TOKEN_EXPIRY_HOURS = 1
    MAX_RESET_ATTEMPTS = 3
    RESET_COOLDOWN_MINUTES = 5

    @staticmethod
    def generate_reset_token() -> tuple[str, str]:
        raw_token = secrets.token_urlsafe(AuthService.RESET_TOKEN_LENGTH)
        hashed_token = hash_token(raw_token)
        return raw_token, hashed_token

    @staticmethod
    async def request_password_reset(
        email: str,
        db: AsyncSession,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        success_message = {
            "message": "If an account with this email exists, password reset instructions have been sent.",
            "success": True,
            "next_step": "check_email"
        }
        try:
            statement = select(User).where(User.email == email)
            result = await db.execute(statement)
            user = result.scalars().first()

            if not user:
                logger.warning(
                    f"Password reset requested for non-existent email: {email}")
                return success_message

            if user.reset_token_expires:
                time_since_last = datetime.utcnow() - (user.reset_token_expires -
                                                       timedelta(hours=AuthService.RESET_TOKEN_EXPIRY_HOURS))
                if time_since_last < timedelta(minutes=AuthService.RESET_COOLDOWN_MINUTES):
                    logger.warning(
                        f"Rate limit: Multiple reset attempts for {email}")
                    return success_message

            raw_token, hashed_token = AuthService.generate_reset_token()
            reset_expires = datetime.utcnow() + timedelta(hours=AuthService.RESET_TOKEN_EXPIRY_HOURS)

            user.reset_token = hashed_token
            user.reset_token_expires = reset_expires
            user.reset_attempts = 0

            await db.commit()

            email_service = get_email_service()
            await email_service.send_reset_email(
                to_email=user.email,
                reset_token=raw_token,
                user_name=user.name or user.email.split('@')[0]
            )
            logger.info(f"Password reset email sent to user {user.id}")

            if ip_address:
                logger.info(
                    f"Password reset requested for user {user.id} from IP {ip_address}")

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error in password reset: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in password reset: {str(e)}")

        return success_message

    @staticmethod
    async def verify_reset_token(
        raw_token: str,
        db: AsyncSession,
        increment_attempts: bool = True
    ) -> Optional[User]:
        try:
            token_hash = hash_token(raw_token)
            statement = select(User).where(User.reset_token == token_hash)

            result = await db.execute(statement)
            user = result.scalars().first()

            if not user:
                return None

            # Check for expiry before incrementing attempts
            if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
                logger.warning(
                    f"Attempted to use expired token for user {user.id}")
                user.reset_token = None
                user.reset_token_expires = None
                await db.commit()
                return None

            if increment_attempts:
                user.reset_attempts = (user.reset_attempts or 0) + 1
                await db.commit()

                if user.reset_attempts >= AuthService.MAX_RESET_ATTEMPTS:
                    logger.warning(
                        f"Max reset attempts exceeded for user {user.id}")
                    user.reset_token = None
                    user.reset_token_expires = None
                    await db.commit()
                    return None

            return user

        except SQLAlchemyError as e:
            logger.error(f"Database error verifying reset token: {str(e)}")
            await db.rollback()
            return None

    @staticmethod
    async def reset_password(
        token: str,
        new_password: str,
        confirm_password: str,
        db: AsyncSession,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

        password_errors = AuthService.validate_password_strength(new_password)
        if password_errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
                                "message": "Weak password", "errors": password_errors})

        user = await AuthService.verify_reset_token(token, db, increment_attempts=False)

        if not user:
            logger.warning(f"Invalid reset token attempted during reset")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid or expired reset token")

        is_same_password = await async_verify_hashed_password(new_password, user.password_hash)
        if is_same_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="New password must be different from current password")

        try:
            hashed_new_password = await async_hashed_password(new_password)
            user.password_hash = hashed_new_password
            user.reset_token = None
            user.reset_token_expires = None
            user.reset_attempts = 0
            user.password_changed_at = datetime.utcnow()

            await db.commit()

            logger.info(f"Password reset successful for user {user.id}")
            if ip_address:
                logger.info(f"Password reset from IP {ip_address}")

            return {"message": "Password has been successfully reset", "success": True, "next_step": "login"}

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Database error resetting password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reset password")

    @staticmethod
    async def change_password(
        user_id: str,  # UUIDs are often strings
        current_password: str,
        new_password: str,
        db: AsyncSession
    ) -> Dict[str, Any]:

        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        is_valid_password = await async_verify_hashed_password(current_password, user.password_hash)
        if not is_valid_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

        is_same_password = await async_verify_hashed_password(new_password, user.password_hash)
        if is_same_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="New password must be different from current password")

        password_errors = AuthService.validate_password_strength(new_password)
        if password_errors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={
                                "message": "Weak password", "errors": password_errors})

        try:
            hashed_new_password = await async_hashed_password(new_password)
            user.password_hash = hashed_new_password
            user.password_changed_at = datetime.utcnow()

            await db.commit()

            logger.info(f"Password changed for user {user_id}")
            return {"message": "Password changed successfully", "success": True}

        except SQLAlchemyError as e:
            await db.rollback()
            logger.error(f"Error changing password: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to change password")

    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession
    ) -> Optional[User]:

        statement = select(User).where(User.email.ilike(email))
        result = await db.execute(statement)
        user = result.scalars().first()

        if not user:
            return None
        
        # Check if account is locked
        if user.failed_login_attempts >= 5:
            # Check if lockout period has passed (e.g., 30 minutes)
            if user.last_failed_login_at:
                lockout_duration = timedelta(minutes=30)
                if datetime.utcnow() - user.last_failed_login_at < lockout_duration:
                    logger.warning(f"Locked account login attempt for user {user.id}")
                    return None  # Still locked
            else:
                # Lockout expired, reset attempts
                user.failed_login_attempts = 0
                user.last_failed_login_at = None

        is_valid = await async_verify_hashed_password(password, user.password_hash)

        try:
            if is_valid:
                user.last_login_at = datetime.utcnow()
                user.failed_login_attempts = 0
                user.last_failed_login_at = None
                await db.commit()
                return user
            else:
                user.failed_login_attempts = (
                    user.failed_login_attempts or 0) + 1
                user.last_failed_login_at = datetime.utcnow()
                if user.failed_login_attempts >= 5:
                    logger.warning(
                        f"Account locked for user {user.id} after 5 failed attempts")

                await db.commit()
                return None
        except SQLAlchemyError:
            await db.rollback()
            return None

    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")
        if not any(c.isupper() for c in password):
            errors.append(
                "Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            errors.append(
                "Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            errors.append(
                "Password must contain at least one special character")
        common_passwords = ["password", "12345678",
                            "qwerty", "abc123", "password123"]
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        return errors


# Create service instance
auth_service = AuthService()
