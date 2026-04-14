from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.response import ApiResponse, success_response
from app.db.session import get_bookings_collection, get_events_collection
from app.modules.auth.dependencies import get_current_user
from app.modules.booking.schemas import (
    BookingCreateRequest,
    BookingResponseData,
    UserBooking,
    BookingDetail
)
from app.modules.event.router import map_db_to_event

router = APIRouter(prefix="", tags=["bookings"])  # Prefix handled at main or inclusion


# ── helpers ──────────────────────────────────────────────────────────
async def _get_event_or_404(event_id_str: str, events_collection):
    """Validate ObjectId format, look up the event, return the doc or 404."""
    try:
        oid = ObjectId(event_id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    event_doc = await events_collection.find_one({"_id": oid})
    if not event_doc:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_doc


# ── POST /bookings ──────────────────────────────────────────────────
@router.post("/bookings", response_model=ApiResponse[BookingResponseData], status_code=status.HTTP_201_CREATED)
async def book_tickets(
    body: BookingCreateRequest,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
):
    # 1. Check event exists
    event_doc = await _get_event_or_404(body.eventId, events_collection)

    # 2. Check event hasn't already passed
    event_dt = event_doc.get("event_start_datetime")
    if event_dt:
        if event_dt.tzinfo is None:
            event_dt = event_dt.replace(tzinfo=timezone.utc)
        if event_dt < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot book tickets for an event that has already passed",
            )

    # 3. Prevent duplicate bookings for the same event by same user
    existing = await bookings_collection.find_one({
        "userId": ObjectId(current_user["_id"]),
        "eventId": body.eventId,
        "status": {"$ne": "cancelled"},  # allow re-booking if previously cancelled
    })
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active booking for this event",
        )

    # 4. Server-side price calculation — never trust client-sent price
    unit_price = float(event_doc.get("price", 0))
    total_price = round(unit_price * body.ticketCount, 2)

    booking_doc = {
        "bookingId": f"bk-{ObjectId()}",
        "userId": ObjectId(current_user["_id"]),
        "eventId": body.eventId,
        "fullName": body.fullName,
        "email": body.email,
        "phoneNumber": body.phoneNumber,
        "ticketCount": body.ticketCount,
        "totalPrice": total_price,
        "status": "upcoming",
    }

    await bookings_collection.insert_one(booking_doc)

    return success_response(
        message="Booking confirmed!",
        data=BookingResponseData(
            bookingId=booking_doc["bookingId"],
            tickets=body.ticketCount,
            totalAmount=total_price,
        ).model_dump(),
    )


# ── GET /users/me/bookings ─────────────────────────────────────────
@router.get("/users/me/bookings", response_model=ApiResponse[dict])
async def get_my_bookings(
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
):
    cursor = bookings_collection.find({"userId": ObjectId(current_user["_id"])})
    items = await cursor.to_list(length=100)

    bookings = []
    for b in items:
        event_doc = await events_collection.find_one({"_id": ObjectId(b["eventId"])})
        if event_doc:
            event_obj = map_db_to_event(event_doc)
            bookings.append(UserBooking(
                bookingId=b["bookingId"],
                event=event_obj,
                ticketCount=b["ticketCount"],
                totalPrice=b["totalPrice"],
                status=b["status"]
            ).model_dump())

    return success_response(data={"bookings": bookings})


# ── GET /bookings/{bookingId} ──────────────────────────────────────
@router.get("/bookings/{bookingId}", response_model=ApiResponse[dict])
async def get_booking_details(
    bookingId: str,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
):
    booking = await bookings_collection.find_one({
        "bookingId": bookingId,
        "userId": ObjectId(current_user["_id"]),
    })

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    event_doc = await events_collection.find_one({"_id": ObjectId(booking["eventId"])})
    if not event_doc:
        raise HTTPException(status_code=404, detail="Event not found")

    event_obj = map_db_to_event(event_doc)

    return success_response(
        data={
            "booking": BookingDetail(
                bookingId=booking["bookingId"],
                qrCode="qr_data_string",
                event=event_obj,
                ticketCount=booking["ticketCount"],
                totalPrice=booking["totalPrice"],
                status=booking["status"],
            ).model_dump()
        }
    )


# ── POST /bookings/{bookingId}/cancel ──────────────────────────────
@router.post("/bookings/{bookingId}/cancel", response_model=ApiResponse[dict])
async def cancel_booking(
    bookingId: str,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
):
    # Check booking exists and belongs to the current user
    booking = await bookings_collection.find_one({
        "bookingId": bookingId,
        "userId": ObjectId(current_user["_id"]),
    })

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking["status"] == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking is already cancelled",
        )

    await bookings_collection.update_one(
        {"_id": booking["_id"]},
        {"$set": {"status": "cancelled"}},
    )

    return success_response(
        message="Cancellation request submitted. Refunds may take 5-7 business days.",
        data={"bookingId": bookingId, "status": "cancelled"},
    )
