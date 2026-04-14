from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection


async def create_profile(
    *,
    user_id: ObjectId,
    full_name: Optional[str],
    display_name: Optional[str],
    bio: Optional[str],
    phone: Optional[str],
    avatar_url: Optional[str],
    profiles_collection: AsyncIOMotorCollection,
) -> dict[str, Any]:
    profile_doc = {
        "user_id": user_id,
        "full_name": full_name,
        "display_name": display_name,
        "bio": bio,
        "phone": phone,
        "avatar_url": avatar_url,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await profiles_collection.insert_one(profile_doc)
    created = await profiles_collection.find_one({"_id": result.inserted_id})
    if not created:
        raise RuntimeError("Profile insertion succeeded but profile could not be reloaded")
    return created


async def find_profile_by_user_id(
    *,
    user_id: ObjectId,
    profiles_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    return await profiles_collection.find_one({"user_id": user_id})


async def update_profile_by_user_id(
    *,
    user_id: ObjectId,
    update_fields: dict[str, Any],
    profiles_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    update = {**update_fields, "updated_at": datetime.utcnow()}
    result = await profiles_collection.update_one({"user_id": user_id}, {"$set": update})
    if result.matched_count == 0:
        return None
    return await profiles_collection.find_one({"user_id": user_id})

