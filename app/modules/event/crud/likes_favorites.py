from __future__ import annotations

from datetime import datetime
from typing import Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection


async def like_event(
    *,
    user_id: ObjectId,
    event_id: ObjectId,
    likes_collection: AsyncIOMotorCollection,
) -> bool:
    # Unique index on (user_id, event_id) ensures idempotency.
    result = await likes_collection.update_one(
        {"user_id": user_id, "event_id": event_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "event_id": event_id,
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    # matched_count means it already existed; upserted_id is set only on insert.
    return result.upserted_id is not None


async def unlike_event(
    *,
    user_id: ObjectId,
    event_id: ObjectId,
    likes_collection: AsyncIOMotorCollection,
) -> bool:
    result = await likes_collection.delete_one({"user_id": user_id, "event_id": event_id})
    return result.deleted_count == 1


async def favorite_event(
    *,
    user_id: ObjectId,
    event_id: ObjectId,
    favorites_collection: AsyncIOMotorCollection,
) -> bool:
    result = await favorites_collection.update_one(
        {"user_id": user_id, "event_id": event_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "event_id": event_id,
                "created_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    return result.upserted_id is not None


async def unfavorite_event(
    *,
    user_id: ObjectId,
    event_id: ObjectId,
    favorites_collection: AsyncIOMotorCollection,
) -> bool:
    result = await favorites_collection.delete_one({"user_id": user_id, "event_id": event_id})
    return result.deleted_count == 1


async def list_favorite_events(
    *,
    user_id: ObjectId,
    favorites_collection: AsyncIOMotorCollection,
    events_collection: AsyncIOMotorCollection,
    page: int,
    limit: int,
) -> tuple[list[dict], int]:
    skip = max(page - 1, 0) * limit

    # Fetch favorites first (so we can preserve ordering), then hydrate events.
    cursor = (
        favorites_collection.find({"user_id": user_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    favorites: list[dict] = []
    async for doc in cursor:
        favorites.append(doc)

    total = await favorites_collection.count_documents({"user_id": user_id})

    event_ids = [f["event_id"] for f in favorites if f.get("event_id") is not None]
    if not event_ids:
        return [], total

    events_cursor = events_collection.find({"_id": {"$in": event_ids}})
    events_by_id: dict[ObjectId, dict] = {}
    async for e in events_cursor:
        events_by_id[e["_id"]] = e

    # Preserve the favorites order (based on created_at descending).
    ordered_events: list[dict] = []
    for f in favorites:
        eid = f.get("event_id")
        if eid in events_by_id:
            ordered_events.append(events_by_id[eid])

    return ordered_events, total

