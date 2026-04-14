from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional

from app.core.response import ApiResponse, success_response
from app.db.session import get_profiles_collection, get_users_collection
from app.modules.auth.router import get_current_user
from app.modules.profile.crud.profiles import (
    find_profile_by_user_id,
    update_profile_by_user_id,
)
from app.modules.profile.schemas.models import ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/users/me", tags=["profile"])


@router.get("", response_model=ApiResponse)
async def get_my_profile(
    current_user=Depends(get_current_user),
    profiles_collection=Depends(get_profiles_collection),
):
    user_id = ObjectId(current_user["_id"])
    profile = await find_profile_by_user_id(
        user_id=user_id, profiles_collection=profiles_collection
    )
    
    return success_response(
        data={
            "user": ProfileResponse(
                id=str(current_user["_id"]),
                name=profile.get("full_name") or current_user.get("full_name") or current_user["email"],
                email=current_user["email"],
                avatarUrl=profile.get("avatar_url"),
                notificationsEnabled=profile.get("notifications_enabled", True)
            ).model_dump()
        }
    )


@router.put("", response_model=ApiResponse)
async def update_my_profile(
    body: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    users_collection=Depends(get_users_collection),
    profiles_collection=Depends(get_profiles_collection),
):
    user_id = ObjectId(current_user["_id"])
    
    update_fields = {}
    if body.name is not None:
        update_fields["full_name"] = body.name
        # Keep user collection in sync
        await users_collection.update_one({"_id": user_id}, {"$set": {"full_name": body.name}})
        
    if body.notificationsEnabled is not None:
        update_fields["notifications_enabled"] = body.notificationsEnabled

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    updated = await update_profile_by_user_id(
        user_id=user_id,
        update_fields=update_fields,
        profiles_collection=profiles_collection,
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Profile not found")

    return success_response(
        message="Profile updated successfully",
        data={
            "user": ProfileResponse(
                id=str(current_user["_id"]),
                name=updated.get("full_name") or current_user["email"],
                email=current_user["email"],
                avatarUrl=updated.get("avatar_url"),
                notificationsEnabled=updated.get("notifications_enabled", True)
            ).model_dump()
        }
    )
