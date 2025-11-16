from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=6, description="New password")
    confirm_password: str = Field(..., min_length=6,
                                  description="Confirm new password")

    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "newPassword123",
                "confirm_password": "newPassword123"
            }
        }


class PasswordResetResponse(BaseModel):
    message: str
    success: bool


class VerifyResetTokenRequest(BaseModel):
    token: str = Field(..., description="Password reset token to verify")
