from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.db.session import get_profiles_collection, get_users_collection
from app.modules.auth.crud.users import (
    create_user,
    find_user_by_email,
    find_user_by_id,
    set_user_otp,
    update_user_roles,
    verify_user_otp,
)
from app.core.response import ApiResponse, success_response
from app.modules.profile.crud.profiles import create_profile, find_profile_by_user_id
from app.modules.auth.schemas.models import (
    AuthDataResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    RegisterRequest,
    SendOtpRequest,
    UserObject,
    VerifyOtpRequest,
)
from app.modules.auth.services.auth_service import (
    decode_access_token,
    hash_otp_code,
    hash_password,
    verify_password,
    create_access_token,
    generate_otp_code,
)
from app.services.email import EmailService
from app.modules.auth.dependencies import get_current_user, bearer_scheme

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=ApiResponse[AuthDataResponse], status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    users_collection=Depends(get_users_collection),
    profiles_collection=Depends(get_profiles_collection),
    settings=Depends(get_settings),
):
    existing = await find_user_by_email(email=body.email, users_collection=users_collection)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if body.password != body.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    password_hash = hash_password(body.password)

    otp_code = generate_otp_code(length=settings.otp_length)
    otp_code_hash = hash_otp_code(otp_code)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)

    user = await create_user(
        email=body.email,
        password_hash=password_hash,
        full_name=body.name,
        roles=["user"],
        is_verified=False,
        otp_code_hash=otp_code_hash,
        otp_expires_at=otp_expires_at,
        users_collection=users_collection,
        settings=settings,
    )

    # Send OTP email
    email_sent = await EmailService.send_otp_email(to_email=user["email"], otp_code=otp_code)

    # Initialize profile document on signup.
    profile = await create_profile(
        user_id=user["_id"],
        full_name=body.name,
        display_name=body.name,
        bio=None,
        phone=None,
        avatar_url=None,
        profiles_collection=profiles_collection,
    )

    token = create_access_token(subject=str(user["_id"]), settings=settings)
    
    user_data = UserObject(
        id=str(user["_id"]),
        name=body.name,
        email=user["email"],
        avatarUrl=profile.get("avatar_url"),
    )

    return success_response(
        message="Created successfully. Please verify your email with the OTP sent.",
        data={
            "token": token,
            "user": user_data.model_dump(),
            "otp_sent": email_sent
        }
    )


@router.post("/login", response_model=ApiResponse[AuthDataResponse])
async def login(
    body: LoginRequest,
    users_collection=Depends(get_users_collection),
    profiles_collection=Depends(get_profiles_collection),
    settings=Depends(get_settings),
):
    user = await find_user_by_email(email=body.email, users_collection=users_collection)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(subject=str(user["_id"]), settings=settings)
    oid = user["_id"]
    profile = await find_profile_by_user_id(
        user_id=oid,
        profiles_collection=profiles_collection,
    )
    
    avatar_url = profile.get("avatar_url") if profile else None
    user_data = UserObject(
        id=str(user["_id"]),
        name=user.get("full_name") or user["email"],
        email=user["email"],
        avatarUrl=avatar_url,
    )

    return success_response(
        data=AuthDataResponse(token=token, user=user_data).model_dump()
    )


@router.post("/logout", response_model=ApiResponse)
async def logout(current_user=Depends(get_current_user)):
    return success_response(message="Logged out successfully")


@router.post("/send-otp", response_model=ApiResponse)
async def send_otp(
    body: SendOtpRequest,
    users_collection=Depends(get_users_collection),
    settings=Depends(get_settings),
):
    user = await find_user_by_email(email=body.email, users_collection=users_collection)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_code = generate_otp_code(length=settings.otp_length)
    otp_code_hash = hash_otp_code(otp_code)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)

    await set_user_otp(
        user_id=user["_id"],
        otp_code_hash=otp_code_hash,
        otp_expires_at=otp_expires_at,
        users_collection=users_collection,
    )

    await EmailService.send_otp_email(to_email=user["email"], otp_code=otp_code)

    return success_response(
        message="OTP sent successfully to the provided email",
        data={"otp_sent": True}
    )


@router.post("/verify-otp", response_model=ApiResponse)
async def verify_otp(
    body: VerifyOtpRequest,
    users_collection=Depends(get_users_collection),
):
    user = await find_user_by_email(email=body.email, users_collection=users_collection)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_code_hash = user.get("otp_code_hash")
    otp_expires_at = user.get("otp_expires_at")
    if not otp_code_hash or not otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not set")

    now = datetime.now(timezone.utc)
    if otp_expires_at.tzinfo is None:
        otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)

    if now > otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")

    if hash_otp_code(body.otp) != otp_code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP")

    await verify_user_otp(user_id=user["_id"], users_collection=users_collection)
    
    return success_response(
        message="Email verified successfully",
        data={"verified": True}
    )


@router.post("/forgot-password", response_model=ApiResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    users_collection=Depends(get_users_collection),
    settings=Depends(get_settings),
):
    user = await find_user_by_email(email=body.email, users_collection=users_collection)
    if not user:
        # Avoid user enumeration by returning success anyway
        return success_response(message="Password reset instructions sent to email")

    otp_code = generate_otp_code(length=settings.otp_length)
    otp_code_hash = hash_otp_code(otp_code)
    otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expire_minutes)

    await set_user_otp(
        user_id=user["_id"],
        otp_code_hash=otp_code_hash,
        otp_expires_at=otp_expires_at,
        users_collection=users_collection,
    )

    await EmailService.send_password_reset_email(to_email=user["email"], otp_code=otp_code)

    return success_response(message="Password reset instructions sent to email")


@router.post("/reset-password", response_model=ApiResponse)
async def reset_password(
    body: ResetPasswordRequest,
    users_collection=Depends(get_users_collection),
):
    user = await find_user_by_email(email=body.email, users_collection=users_collection)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    otp_code_hash = user.get("otp_code_hash")
    otp_expires_at = user.get("otp_expires_at")
    if not otp_code_hash or not otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not set")

    now = datetime.now(timezone.utc)
    if otp_expires_at.tzinfo is None:
        otp_expires_at = otp_expires_at.replace(tzinfo=timezone.utc)

    if now > otp_expires_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")

    # The spec mentions "token": "reset_token_or_otp"
    if hash_otp_code(body.token) != otp_code_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token or OTP")

    new_password_hash = hash_password(body.newPassword)
    
    # Update password and clear OTP
    from app.modules.auth.crud.users import update_user_password
    await update_user_password(
        user_id=user["_id"],
        password_hash=new_password_hash,
        users_collection=users_collection
    )

    return success_response(message="Password has been successfully reset")
