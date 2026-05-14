import time

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UpdateProfileRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
    responses={401: {"description": "Unauthorized"}},
)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the authenticated user's profile",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Validation error"},
    },
)
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if body.display_name is not None:
        current_user.display_name = body.display_name
    if body.bio is not None:
        current_user.bio = body.bio
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    if body.profile_public is not None:
        current_user.profile_public = body.profile_public
    if body.stats_public is not None:
        current_user.stats_public = body.stats_public
    await session.commit()
    await session.refresh(current_user)
    return current_user


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Upload or replace the authenticated user's avatar image",
    responses={
        400: {"description": "Invalid file type or file too large"},
        401: {"description": "Unauthorized"},
        502: {"description": "Storage upload failed or not configured"},
    },
)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, detail="File must be image/jpeg, image/png, or image/webp"
        )

    data = await file.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 2 MB limit")

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=502, detail="Storage not configured")

    object_path = f"avatars/{current_user.id}"
    upload_url = f"{settings.supabase_url}/storage/v1/object/{object_path}"

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            upload_url,
            content=data,
            headers={
                "Authorization": f"Bearer {settings.supabase_anon_key}",
                "Content-Type": content_type,
                "x-upsert": "true",
            },
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail="Storage upload failed")

    timestamp = int(time.time())
    cdn_url = (
        f"{settings.supabase_url}/storage/v1/object/public/{object_path}?t={timestamp}"
    )
    current_user.avatar_url = cdn_url
    await session.commit()
    await session.refresh(current_user)
    return current_user
