from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.response import ApiResponse, success_response
from app.db.session import get_event_favorites_collection, get_events_collection
from app.modules.auth.dependencies import get_current_user
from app.modules.event.router import map_db_to_event

router = APIRouter(prefix="/users/me/favorites", tags=["favorites"])


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


# ── GET / ──────────────────────────────────────────────────────────
@router.get("", response_model=ApiResponse[dict])
async def get_favorites(
    current_user=Depends(get_current_user),
    favorites_collection=Depends(get_event_favorites_collection),
    events_collection=Depends(get_events_collection),
):
    cursor = favorites_collection.find({"user_id": ObjectId(current_user["_id"])})
    items = await cursor.to_list(length=100)

    favorites = []
    for f in items:
        event_doc = await events_collection.find_one({"_id": ObjectId(f["event_id"])})
        if event_doc:
            event_obj = map_db_to_event(event_doc)
            # Spec response for favorites only includes a subset of fields
            favorites.append({
                "id": event_obj.id,
                "title": event_obj.title,
                "price": event_obj.price,
                "imageUrl": event_obj.imageUrl
            })

    return success_response(data={"favorites": favorites})


# ── POST /{eventId} ───────────────────────────────────────────────
@router.post("/{eventId}", response_model=ApiResponse[dict])
async def add_favorite(
    eventId: str,
    current_user=Depends(get_current_user),
    favorites_collection=Depends(get_event_favorites_collection),
    events_collection=Depends(get_events_collection),
):
    # Verify event actually exists before favoriting
    await _get_event_or_404(eventId, events_collection)
    oid = ObjectId(eventId)

    await favorites_collection.update_one(
        {"user_id": ObjectId(current_user["_id"]), "event_id": oid},
        {"$set": {"user_id": ObjectId(current_user["_id"]), "event_id": oid}},
        upsert=True
    )

    return success_response(message="Event added to favorites")


# ── DELETE /{eventId} ──────────────────────────────────────────────
@router.delete("/{eventId}", response_model=ApiResponse[dict])
async def remove_favorite(
    eventId: str,
    current_user=Depends(get_current_user),
    favorites_collection=Depends(get_event_favorites_collection),
):
    try:
        oid = ObjectId(eventId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event ID format")

    result = await favorites_collection.delete_one({
        "user_id": ObjectId(current_user["_id"]),
        "event_id": oid
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")

    return success_response(message="Event removed from favorites")
