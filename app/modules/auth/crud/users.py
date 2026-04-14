from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic_settings import BaseSettings


async def find_user_by_email(
    *,
    email: str,
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    return await users_collection.find_one({"email": email})


async def find_user_by_id(
    *,
    user_id: ObjectId,
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    return await users_collection.find_one({"_id": user_id})


async def create_user(
    *,
    email: str,
    password_hash: str,
    full_name: Optional[str],
    roles: list[str],
    is_verified: bool,
    otp_code_hash: Optional[str],
    otp_expires_at: Optional[datetime],
    users_collection: AsyncIOMotorCollection,
    settings: BaseSettings,
) -> dict[str, Any]:
    # `settings` is currently unused, but accepted to keep the CRUD layer consistent
    # with future config (e.g., collection names).
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "full_name": full_name,
        # New model: roles as a list.
        "roles": roles,
        # Legacy single role field for backward compatibility.
        "role": (roles[0] if roles else "user"),
        "is_verified": is_verified,
        "otp_code_hash": otp_code_hash,
        "otp_expires_at": otp_expires_at,
        "created_at": datetime.utcnow(),
    }

    result = await users_collection.insert_one(user_doc)
    created = await users_collection.find_one({"_id": result.inserted_id})
    if not created:
        raise RuntimeError("User insertion succeeded but user could not be reloaded")
    return created


async def update_user_roles(
    *,
    user_id: ObjectId,
    roles: list[str],
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    update = {
        "$set": {
            "roles": roles,
            "role": (roles[0] if roles else "user"),
        }
    }
    result = await users_collection.update_one({"_id": user_id}, update)
    if result.matched_count == 0:
        return None
    return await users_collection.find_one({"_id": user_id})


async def set_user_otp(
    *,
    user_id: ObjectId,
    otp_code_hash: str,
    otp_expires_at: datetime,
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"otp_code_hash": otp_code_hash, "otp_expires_at": otp_expires_at}},
    )
    return await users_collection.find_one({"_id": user_id})


async def verify_user_otp(
    *,
    user_id: ObjectId,
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {"is_verified": True},
            "$unset": {"otp_code_hash": "", "otp_expires_at": ""},
        },
    )
    return await users_collection.find_one({"_id": user_id})


async def update_user_password(
    *,
    user_id: ObjectId,
    password_hash: str,
    users_collection: AsyncIOMotorCollection,
) -> Optional[dict[str, Any]]:
    await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {"password_hash": password_hash},
            "$unset": {"otp_code_hash": "", "otp_expires_at": ""},
        },
    )
    return await users_collection.find_one({"_id": user_id})
