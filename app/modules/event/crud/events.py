from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection


def _make_geo(latitude: float, longitude: float) -> dict[str, Any]:
    # MongoDB expects [longitude, latitude] for Point.
    return {"type": "Point", "coordinates": [longitude, latitude]}


async def create_event(
    *,
    organizer_user_id: ObjectId,
    payload: dict[str, Any],
    events_collection: AsyncIOMotorCollection,
) -> dict[str, Any]:
    now = datetime.utcnow()
    latitude = payload["latitude"]
    longitude = payload["longitude"]
    doc = {
        **payload,
        "organizer_user_id": organizer_user_id,
        "geo": _make_geo(latitude=latitude, longitude=longitude),
        "created_at": now,
        "updated_at": now,
    }
    result = await events_collection.insert_one(doc)
    created = await events_collection.find_one({"_id": result.inserted_id})
    if not created:
        raise RuntimeError("Event insertion succeeded but event could not be reloaded")
    return created


async def find_event_by_id(
    *,
    event_id: ObjectId,
    events_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    return await events_collection.find_one({"_id": event_id})


async def list_events(
    *,
    filter_doc: dict[str, Any],
    page: int,
    limit: int,
    events_collection: AsyncIOMotorCollection,
) -> tuple[list[dict[str, Any]], int]:
    skip = max(page - 1, 0) * limit
    cursor = (
        events_collection.find(filter_doc)
        .sort("event_start_datetime", 1)
        .skip(skip)
        .limit(limit)
    )
    items: list[dict[str, Any]] = []
    async for doc in cursor:
        items.append(doc)
    total = await events_collection.count_documents(filter_doc)
    return items, total


async def update_event_by_id(
    *,
    event_id: ObjectId,
    update_fields: dict[str, Any],
    events_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    now = datetime.utcnow()

    # If lat/long updates are provided together, regenerate geo.
    if "latitude" in update_fields and "longitude" in update_fields:
        update_fields["geo"] = _make_geo(
            latitude=update_fields["latitude"],
            longitude=update_fields["longitude"],
        )

    update_fields["updated_at"] = now

    result = await events_collection.update_one(
        {"_id": event_id},
        {"$set": update_fields},
    )
    if result.matched_count == 0:
        return None
    return await events_collection.find_one({"_id": event_id})


async def delete_event_by_id(
    *,
    event_id: ObjectId,
    events_collection: AsyncIOMotorCollection,
) -> bool:
    result = await events_collection.delete_one({"_id": event_id})
    return result.deleted_count == 1

