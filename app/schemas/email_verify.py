from pydantic import BaseModel, EmailStr

class EmailVerificationRequest(BaseModel):
    email: EmailStr
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class MessageResponse(BaseModel):
    message: str
