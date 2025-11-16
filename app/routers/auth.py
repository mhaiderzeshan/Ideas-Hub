from typing import Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
    VerifyResetTokenRequest
)
from app.crud.auth import auth_service
from app.db.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Constants (no change)
RESET_TOKEN_EXPIRY_HOURS = 1
MIN_REQUEST_INTERVAL_MINUTES = 5


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> PasswordResetResponse:
    """
    Request password reset email.
    """
    try:
        # This call now correctly passes an AsyncSession to your service
        result = await auth_service.request_password_reset(
            email=request.email,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


@router.post("/verify-reset-token")
async def verify_reset_token(
    request: VerifyResetTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verify if a reset token is valid.
    """
    try:
        user = await auth_service.verify_reset_token(request.token, db)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        return {
            "message": "Token is valid",
            "success": True,
            "email": user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify token"
        )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> PasswordResetResponse:
    """
    Reset password using token.
    """
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    try:
        result = await auth_service.reset_password(
            token=request.token,
            new_password=request.new_password,
            confirm_password=request.confirm_password,
            db=db
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.post("/resend-reset-email", response_model=PasswordResetResponse)
async def resend_reset_email(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> PasswordResetResponse:
    """
    Resend password reset email with rate limiting.
    """
    try:
        statement = select(User).where(User.email == request.email)
        result = await db.execute(statement)
        user = result.scalars().first()

        if user and user.reset_token_expires:
            token_created_at = user.reset_token_expires - \
                timedelta(hours=RESET_TOKEN_EXPIRY_HOURS)
            time_since_last_request = datetime.utcnow() - token_created_at

            if time_since_last_request < timedelta(minutes=MIN_REQUEST_INTERVAL_MINUTES):
                remaining_seconds = (timedelta(
                    minutes=MIN_REQUEST_INTERVAL_MINUTES) - time_since_last_request).total_seconds()
                # Show at least 1 minute
                remaining_minutes = max(1, round(remaining_seconds / 60))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining_minutes} minute(s) before requesting another reset email"
                )

        result = await auth_service.request_password_reset(
            email=request.email,
            db=db
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend reset email"
        )
