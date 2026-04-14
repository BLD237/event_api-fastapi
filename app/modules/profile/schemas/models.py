from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr


class ProfileResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    avatarUrl: Optional[str] = None
    notificationsEnabled: bool = True


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    notificationsEnabled: Optional[bool] = None
