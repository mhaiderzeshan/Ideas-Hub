from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from fastapi.responses import Response

from app.schemas.email_verify import (
    EmailVerificationRequest,
    ResendVerificationRequest,
    MessageResponse
)
from app.db.database import get_db
from app.db.models.user import User
from app.services.email_verification import EmailVerificationService
from app.services.email_service import EmailService
from app.core.dependencies import get_current_user
from app.core.config import settings

router = APIRouter(tags=["Email Verification"])


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify user's email with token"""
    try:
        # Get user by email
        result = await db.execute(
            select(User).where(User.email == request.email)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify the token
        if (not user.email_verification_token or
            user.email_verification_token != request.token or
            user.email_verification_token_expiry is None or
                user.email_verification_token_expiry < datetime.utcnow()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )

        # Update user
        user.is_email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_token_expiry = None

        await db.commit()

        return {"message": "Email verified successfully"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/verify-email")
async def verify_email_get(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify user's email with token from URL (for email links)"""
    try:
        success = await EmailVerificationService.verify_email(db, token)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )

        # Return HTML response for better UX
        return Response(
            content="""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Email Verified</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                        text-align: center;
                        max-width: 400px;
                    }
                    .success-icon {
                        font-size: 64px;
                        color: #10b981;
                        margin-bottom: 20px;
                    }
                    h1 {
                        color: #1f2937;
                        margin-bottom: 10px;
                    }
                    p {
                        color: #6b7280;
                        margin-bottom: 30px;
                    }
                    .button {
                        display: inline-block;
                        padding: 12px 30px;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                        transition: background 0.3s;
                    }
                    .button:hover {
                        background: #5568d3;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✓</div>
                    <h1>Email Verified!</h1>
                    <p>Your email has been successfully verified. You can now log in to your account.</p>
                    <a href="#" class="button">Go to Login</a>
                </div>
                <script>
                    // Redirect after 3 seconds
                    setTimeout(() => {
                        window.location.href = '""" + settings.FRONTEND_URL + """/login';
                    }, 3000);
                </script>
            </body>
            </html>
            """,
            media_type="text/html"
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Resend verification email"""
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if user exists or not (security best practice)
        return {"message": "If the email exists and is not verified, a verification email has been sent."}

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )

    # Generate new token
    token = await EmailVerificationService.create_verification_token(db, user)

    # Send verification email in background
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    background_tasks.add_task(
        EmailService.send_verification_email,
        user.email,
        user.name,
        verification_url
    )

    return {"message": "Verification email sent successfully"}


@router.get("/verification-status")
async def get_verification_status(
    current_user: User = Depends(get_current_user)
):
    """Check if current user's email is verified"""
    return {
        "email": current_user.email,
        "is_verified": current_user.is_email_verified,
        "verified_at": current_user.email_verified_at
    }
