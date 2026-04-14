from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.response import ApiResponse, success_response
from app.db.session import get_bookings_collection, get_events_collection
from app.modules.auth.router import get_current_user
from app.modules.booking.schemas import (
    BookingCreateRequest,
    BookingResponseData,
    UserBooking,
    BookingDetail
)
from app.modules.event.router import map_db_to_event

router = APIRouter(prefix="", tags=["bookings"]) # Prefix handled at main or inclusion


@router.post("/bookings", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def book_tickets(
    body: BookingCreateRequest,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
):
    booking_doc = body.model_dump()
    booking_doc["userId"] = ObjectId(current_user["_id"])
    booking_doc["status"] = "upcoming"
    booking_doc["bookingId"] = f"bk-{ObjectId()}"
    
    await bookings_collection.insert_one(booking_doc)
    
    return success_response(
        message="Booking confirmed!",
        data=BookingResponseData(
            bookingId=booking_doc["bookingId"],
            tickets=body.ticketCount,
            totalAmount=body.totalPrice
        ).model_dump()
    )


@router.get("/users/me/bookings", response_model=ApiResponse)
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


@router.get("/bookings/{bookingId}", response_model=ApiResponse)
async def get_booking_details(
    bookingId: str,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
):
    booking = await bookings_collection.find_one({
        "bookingId": bookingId, 
        "userId": ObjectId(current_user["_id"])
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
                status=booking["status"]
            ).model_dump()
        }
    )


@router.post("/bookings/{bookingId}/cancel", response_model=ApiResponse)
async def cancel_booking(
    bookingId: str,
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
):
    result = await bookings_collection.update_one(
        {"bookingId": bookingId, "userId": ObjectId(current_user["_id"])},
        {"$set": {"status": "cancelled"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
        
    return success_response(
        message="Cancellation request submitted. Refunds may take 5-7 business days.",
        data={"bookingId": bookingId, "status": "cancelled"}
    )
