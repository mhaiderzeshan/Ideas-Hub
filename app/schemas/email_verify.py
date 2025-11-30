from pydantic import BaseModel, EmailStr

class MessageResponse(BaseModel):
    message: str

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    token: str

class TokenVerificationRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr
