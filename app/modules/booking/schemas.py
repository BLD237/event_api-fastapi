from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from app.modules.event.schemas.models import EventObject


class BookingCreateRequest(BaseModel):
    eventId: str
    fullName: str
    email: str
    phoneNumber: str
    ticketCount: int
    totalPrice: float


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
