from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator, EmailStr
from app.modules.event.schemas.models import EventObject


class BookingCreateRequest(BaseModel):
    eventId: str
    fullName: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phoneNumber: str = Field(..., min_length=8, max_length=20)
    ticketCount: int = Field(..., ge=1, le=20, description="Number of tickets (1-20)")

    # totalPrice is intentionally NOT accepted from the client.
    # The server computes it from event.price * ticketCount.

    @field_validator("phoneNumber")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.lstrip("+").isdigit():
            raise ValueError("Phone number must contain only digits, spaces, hyphens, or a leading +")
        return v


class BookingResponseData(BaseModel):
    bookingId: str
    tickets: int
    totalAmount: float


class UserBooking(BaseModel):
    bookingId: str
    event: EventObject
    ticketCount: int
    totalPrice: float
    status: str  # "upcoming", "completed", "cancelled"


class BookingDetail(BaseModel):
    bookingId: str
    qrCode: str
    event: EventObject
    ticketCount: int
    totalPrice: float
    status: str
