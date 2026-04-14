from __future__ import annotations

from datetime import datetime
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.core.response import ApiResponse, success_response
from app.db.session import get_reviews_collection, get_events_collection, get_bookings_collection
from app.modules.auth.router import get_current_user
from app.modules.event.router import map_db_to_event

router = APIRouter(prefix="", tags=["reviews"])


class ReviewSubmitRequest(BaseModel):
    rating: int
    reviewText: str


@router.get("/users/me/reviews", response_model=ApiResponse)
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


@router.get("/users/me/reviews/pending", response_model=ApiResponse)
async def get_pending_reviews(
    current_user=Depends(get_current_user),
    bookings_collection=Depends(get_bookings_collection),
    events_collection=Depends(get_events_collection),
    reviews_collection=Depends(get_reviews_collection),
):
    # Find events the user attended but hasn't reviewed
    cursor = bookings_collection.find({
        "userId": ObjectId(current_user["_id"]),
        "status": "upcoming" # In real app, would be 'completed'
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


@router.post("/events/{eventId}/reviews", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(
    eventId: str,
    body: ReviewSubmitRequest,
    current_user=Depends(get_current_user),
    reviews_collection=Depends(get_reviews_collection),
):
    try:
        oid = ObjectId(eventId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")
        
    review_doc = {
        "user_id": ObjectId(current_user["_id"]),
        "event_id": oid,
        "rating": body.rating,
        "reviewText": body.reviewText,
        "created_at": datetime.utcnow(),
        "likes": 0
    }
    
    await reviews_collection.insert_one(review_doc)
    
    return success_response(
        message="Review submitted successfully!",
        data={
            "rating": body.rating,
            "reviewText": body.reviewText
        }
    )
