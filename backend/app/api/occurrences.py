import time
import uuid
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupMember
from app.models.scheduler import NightOccurrence, NightSeries, OccurrencePhoto, Rsvp
from app.models.user import User
from app.schemas.scheduler import (
    MyOccurrenceItem,
    OccurrenceCreate,
    OccurrencePhotoOut,
    OccurrenceResponse,
    OccurrenceUpdate,
    RsvpCreate,
    RsvpOut,
)

router = APIRouter(tags=["occurrences"])

_ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB


@router.get(
    "/me/occurrences",
    response_model=list[MyOccurrenceItem],
    summary="List upcoming (or past) occurrences across all the user's groups",
    responses={401: {"description": "Unauthorized"}},
)
async def list_my_occurrences(
    past: bool = Query(False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    member_result = await session.execute(
        select(GroupMember).where(GroupMember.user_id == current_user.id)
    )
    group_ids = [m.group_id for m in member_result.scalars().all()]
    if not group_ids:
        return []

    today = date.today()
    if past:
        date_filter = NightOccurrence.occurrence_date < today
        order = NightOccurrence.occurrence_date.desc()
    else:
        date_filter = NightOccurrence.occurrence_date >= today
        order = NightOccurrence.occurrence_date.asc()

    result = await session.execute(
        select(NightOccurrence, NightSeries, Group)
        .join(NightSeries, NightOccurrence.series_id == NightSeries.id)
        .join(Group, NightSeries.group_id == Group.id)
        .where(NightSeries.group_id.in_(group_ids))
        .where(date_filter)
        .where(NightOccurrence.status != "cancelled")
        .order_by(order, NightOccurrence.start_time.asc())
    )
    rows = result.all()

    if not rows:
        return []

    occurrence_ids = [occ.id for occ, _, _ in rows]
    rsvp_result = await session.execute(
        select(Rsvp)
        .where(Rsvp.occurrence_id.in_(occurrence_ids))
        .where(Rsvp.user_id == current_user.id)
    )
    my_rsvps = {r.occurrence_id: r.response for r in rsvp_result.scalars().all()}

    return [
        {
            "id": str(occ.id),
            "occurrence_date": occ.occurrence_date.isoformat(),
            "start_time": str(occ.start_time),
            "end_time": str(occ.end_time) if occ.end_time else None,
            "status": occ.status,
            "notes": occ.notes,
            "series_id": str(series.id),
            "series_title": series.title,
            "group_id": str(group.id),
            "group_name": group.name,
            "my_rsvp": my_rsvps.get(occ.id),
        }
        for occ, series, group in rows
    ]


async def _get_occurrence_member(
    occurrence_id: uuid.UUID, user: User, session: AsyncSession
) -> tuple[NightOccurrence, GroupMember]:
    occ = await session.get(NightOccurrence, occurrence_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    series = await session.get(NightSeries, occ.series_id)
    member = await session.get(GroupMember, (series.group_id, user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return occ, member


@router.post(
    "/series/{series_id}/occurrences",
    response_model=OccurrenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a one-off occurrence for a series (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Series not found"},
    },
)
async def create_occurrence(
    series_id: uuid.UUID,
    body: OccurrenceCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    series = await session.get(NightSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    member = await session.get(GroupMember, (series.group_id, current_user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    occ = NightOccurrence(series_id=series_id, is_auto_generated=False, **body.model_dump())
    session.add(occ)
    await session.commit()
    await session.refresh(occ)
    return occ


@router.get(
    "/occurrences/{occurrence_id}",
    response_model=OccurrenceResponse,
    summary="Get a single occurrence with RSVP counts",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Occurrence not found"},
    },
)
async def get_occurrence(
    occurrence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    occ, _ = await _get_occurrence_member(occurrence_id, current_user, session)
    counts = await _rsvp_counts(occurrence_id, session)
    resp = OccurrenceResponse.model_validate(occ)
    resp.rsvp_counts = counts
    return resp


@router.patch(
    "/occurrences/{occurrence_id}",
    response_model=OccurrenceResponse,
    summary="Update an occurrence (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Occurrence not found"},
    },
)
async def update_occurrence(
    occurrence_id: uuid.UUID,
    body: OccurrenceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    occ, member = await _get_occurrence_member(occurrence_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    updates = body.model_dump(exclude_unset=True)

    if updates.get("status") == "postponed" and "postponed_from_date" not in updates:
        updates["postponed_from_date"] = occ.occurrence_date

    for field, value in updates.items():
        setattr(occ, field, value)

    await session.commit()
    await session.refresh(occ)
    counts = await _rsvp_counts(occurrence_id, session)
    resp = OccurrenceResponse.model_validate(occ)
    resp.rsvp_counts = counts
    return resp


@router.post(
    "/occurrences/{occurrence_id}/rsvp",
    response_model=RsvpOut,
    summary="Submit or update an RSVP for an occurrence",
    responses={
        400: {"description": "Cannot RSVP to a cancelled occurrence"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Occurrence not found"},
    },
)
async def upsert_rsvp(
    occurrence_id: uuid.UUID,
    body: RsvpCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    occ, _ = await _get_occurrence_member(occurrence_id, current_user, session)
    if occ.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot RSVP to a cancelled occurrence")

    result = await session.execute(
        select(Rsvp)
        .where(Rsvp.occurrence_id == occurrence_id)
        .where(Rsvp.user_id == current_user.id)
    )
    rsvp = result.scalar_one_or_none()

    if rsvp:
        rsvp.response = body.response
        rsvp.note = body.note
        rsvp.responded_at = datetime.now(timezone.utc)
    else:
        rsvp = Rsvp(
            occurrence_id=occurrence_id,
            user_id=current_user.id,
            response=body.response,
            note=body.note,
        )
        session.add(rsvp)

    await session.commit()
    await session.refresh(rsvp)

    user_result = await session.execute(select(User).where(User.id == current_user.id))
    user = user_result.scalar_one()
    out = RsvpOut.model_validate(rsvp)
    out.username = user.username
    return out


@router.get(
    "/occurrences/{occurrence_id}/rsvps",
    response_model=list[RsvpOut],
    summary="List RSVPs for an occurrence",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Occurrence not found"},
    },
)
async def list_rsvps(
    occurrence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_occurrence_member(occurrence_id, current_user, session)

    result = await session.execute(
        select(Rsvp, User)
        .join(User, Rsvp.user_id == User.id)
        .where(Rsvp.occurrence_id == occurrence_id)
        .order_by(Rsvp.responded_at)
    )
    rsvps = []
    for rsvp, user in result.all():
        out = RsvpOut.model_validate(rsvp)
        out.username = user.username
        rsvps.append(out)
    return rsvps


@router.get(
    "/occurrences/{occurrence_id}/photos",
    response_model=list[OccurrencePhotoOut],
    summary="List photos uploaded to an occurrence",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Occurrence not found"},
    },
)
async def list_photos(
    occurrence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_occurrence_member(occurrence_id, current_user, session)

    result = await session.execute(
        select(OccurrencePhoto, User)
        .join(User, OccurrencePhoto.uploaded_by == User.id)
        .where(OccurrencePhoto.occurrence_id == occurrence_id)
        .order_by(OccurrencePhoto.created_at.asc())
    )
    photos = []
    for photo, user in result.all():
        out = OccurrencePhotoOut.model_validate(photo)
        out.username = user.username
        photos.append(out)
    return photos


@router.post(
    "/occurrences/{occurrence_id}/photos",
    response_model=OccurrencePhotoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a photo to an occurrence",
    responses={
        400: {"description": "Invalid file type or file too large"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member of this group"},
        404: {"description": "Occurrence not found"},
        502: {"description": "Storage upload failed or not configured"},
    },
)
async def upload_photo(
    occurrence_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_occurrence_member(occurrence_id, current_user, session)

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_PHOTO_TYPES:
        raise HTTPException(status_code=400, detail="File must be image/jpeg, image/png, or image/webp")

    data = await file.read(_MAX_PHOTO_BYTES + 1)
    if len(data) > _MAX_PHOTO_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=502, detail="Storage not configured")

    photo_id = uuid.uuid4()
    object_path = f"occurrence-photos/{occurrence_id}/{photo_id}"
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
    cdn_url = f"{settings.supabase_url}/storage/v1/object/public/{object_path}?t={timestamp}"

    photo = OccurrencePhoto(
        id=photo_id,
        occurrence_id=occurrence_id,
        uploaded_by=current_user.id,
        photo_url=cdn_url,
    )
    session.add(photo)
    await session.commit()
    await session.refresh(photo)

    out = OccurrencePhotoOut.model_validate(photo)
    out.username = current_user.username
    return out


@router.delete(
    "/occurrences/{occurrence_id}/photos/{photo_id}",
    status_code=204,
    summary="Delete a photo from an occurrence (uploader or organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Cannot delete this photo"},
        404: {"description": "Photo not found"},
    },
)
async def delete_photo(
    occurrence_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _, member = await _get_occurrence_member(occurrence_id, current_user, session)

    photo = await session.get(OccurrencePhoto, photo_id)
    if not photo or photo.occurrence_id != occurrence_id:
        raise HTTPException(status_code=404, detail="Photo not found")

    is_organiser = member.role in ("organiser", "owner")
    is_uploader = photo.uploaded_by == current_user.id
    if not is_organiser and not is_uploader:
        raise HTTPException(status_code=403, detail="Cannot delete this photo")

    await session.delete(photo)
    await session.commit()


async def _rsvp_counts(occurrence_id: uuid.UUID, session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {"yes": 0, "no": 0, "maybe": 0}
    result = await session.execute(select(Rsvp).where(Rsvp.occurrence_id == occurrence_id))
    for rsvp in result.scalars().all():
        if rsvp.response in counts:
            counts[rsvp.response] += 1
    return counts
