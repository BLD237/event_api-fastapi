from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.response import ApiResponse, success_response
from app.db.session import get_reviews_collection, get_events_collection, get_bookings_collection
from app.modules.auth.dependencies import get_current_user
from app.modules.event.router import map_db_to_event

router = APIRouter(prefix="", tags=["reviews"])


class ReviewSubmitRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    reviewText: str = Field(..., min_length=10, max_length=2000, description="Review text (10-2000 characters)")


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


# ── GET /users/me/reviews ──────────────────────────────────────────
@router.get("/users/me/reviews", response_model=ApiResponse[dict])
async def get_my_reviews(
    current_user=Depends(get_current_user),
    reviews_collection=Depends(get_reviews_collection),
    events_collection=Depends(get_events_collection),
):
    cursor = reviews_collection.find({"user_id": ObjectId(current_user["_id"])})
    items = await cursor.to_list(length=100)

    reviews = []
    for r in items:
        event_doc = await events_collection.find_one({"_id": ObjectId(r["event_id"])})
        if event_doc:
            event_obj = map_db_to_event(event_doc)
            reviews.append({
                "id": str(r["_id"]),
                "event": {
                    "id": event_obj.id,
                    "title": event_obj.title,
                    "imageUrl": event_obj.imageUrl
                },
                "rating": r["rating"],
                "review": r["reviewText"],
                "reviewDate": r.get("created_at").strftime("%b %d, %Y") if "created_at" in r else "N/A",
                "likes": r.get("likes", 0)
            })

    return success_response(data={"reviews": reviews})


# ── GET /users/me/reviews/pending ──────────────────────────────────
@router.get("/users/me/reviews/pending", response_model=ApiResponse[dict])
async def get_pending_reviews(
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
    reviews_collection=Depends(get_reviews_collection),
):
    # Find events the user attended but hasn't reviewed
    cursor = bookings_collection.find({
        "userId": ObjectId(current_user["_id"]),
        "status": "upcoming"  # In real app, would be 'completed'
    })
    bookings = await cursor.to_list(length=100)

    pending = []
    for b in bookings:
        # Check if already reviewed
        already_reviewed = await reviews_collection.find_one({
            "user_id": ObjectId(current_user["_id"]),
            "event_id": ObjectId(b["eventId"])
        })

        if not already_reviewed:
            event_doc = await events_collection.find_one({"_id": ObjectId(b["eventId"])})
            if event_doc:
                event_obj = map_db_to_event(event_doc)
                pending.append({
                    "id": event_obj.id,
                    "title": event_obj.title,
                    "date": event_obj.date,
                    "imageUrl": event_obj.imageUrl
                })

    return success_response(data={"pendingReviews": pending})


# ── POST /events/{eventId}/reviews ─────────────────────────────────
@router.post("/events/{eventId}/reviews", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def submit_review(
    eventId: str,
    body: ReviewSubmitRequest,
    current_user=Depends(get_current_user),
    reviews_collection=Depends(get_reviews_collection),
    events_collection=Depends(get_events_collection),
    bookings_collection=Depends(get_bookings_collection),
):
    # 1. Check event exists
    event_doc = await _get_event_or_404(eventId, events_collection)
    event_oid = event_doc["_id"]
    user_oid = ObjectId(current_user["_id"])

    # 2. Check user actually booked (attended) this event
    booking = await bookings_collection.find_one({
        "userId": user_oid,
        "eventId": eventId,
        "status": {"$ne": "cancelled"},
    })
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only review events you have booked",
        )

    # 3. Prevent duplicate reviews
    existing_review = await reviews_collection.find_one({
        "user_id": user_oid,
        "event_id": event_oid,
    })
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this event",
        )

    review_doc = {
        "user_id": user_oid,
        "event_id": event_oid,
        "rating": body.rating,
        "reviewText": body.reviewText,
        "created_at": datetime.now(timezone.utc),
        "likes": 0,
    }

    await reviews_collection.insert_one(review_doc)

    return success_response(
        message="Review submitted successfully!",
        data={
            "rating": body.rating,
            "reviewText": body.reviewText,
        },
    )
