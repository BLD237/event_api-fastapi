from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


Role = Literal["user", "admin", "organizers"]


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    confirmPassword: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SendOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str  # This is the OTP or reset token
    newPassword: str = Field(min_length=8, max_length=256)


class UserObject(BaseModel):
    id: str
    name: str
    email: EmailStr
    avatarUrl: Optional[str] = None


class AuthDataResponse(BaseModel):
    token: str
    user: UserObject


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: Optional[str] = None
    roles: list[Role] = ["user"]


class UpdateRoleRequest(BaseModel):
    roles: list[Role]


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    roles: list[Role] = ["user"]
    is_verified: bool = False
