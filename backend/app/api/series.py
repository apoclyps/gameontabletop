import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupMember
from app.models.scheduler import NightOccurrence, NightSeries
from app.models.user import User
from app.schemas.scheduler import (
    OccurrenceResponse,
    SeriesCreate,
    SeriesResponse,
    SeriesUpdate,
)
from app.services.recurrence import ensure_occurrences_generated

router = APIRouter(tags=["series"])


async def _get_group_member(
    group_id: uuid.UUID, user: User, session: AsyncSession
) -> tuple[Group, GroupMember]:
    group = await session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    member = await session.get(GroupMember, (group_id, user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return group, member


async def _get_series_member(
    series_id: uuid.UUID, user: User, session: AsyncSession
) -> tuple[NightSeries, GroupMember]:
    series = await session.get(NightSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    member = await session.get(GroupMember, (series.group_id, user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return series, member


@router.post(
    "/groups/{group_id}/series",
    response_model=SeriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a recurring game night series for a group (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Group not found"},
    },
)
async def create_series(
    group_id: uuid.UUID,
    body: SeriesCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _, member = await _get_group_member(group_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    series = NightSeries(
        group_id=group_id,
        created_by=current_user.id,
        **body.model_dump(),
    )
    session.add(series)
    await session.commit()
    await session.refresh(series)

    if series.series_start_date:
        await ensure_occurrences_generated(series, session)

    return series


@router.get(
    "/groups/{group_id}/series",
    response_model=list[SeriesResponse],
    summary="List series for a group",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Group not found"},
    },
)
async def list_series(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_group_member(group_id, current_user, session)
    result = await session.execute(
        select(NightSeries)
        .where(NightSeries.group_id == group_id)
        .order_by(NightSeries.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/series/{series_id}",
    response_model=SeriesResponse,
    summary="Get a series by ID",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Series not found"},
    },
)
async def get_series(
    series_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    series, _ = await _get_series_member(series_id, current_user, session)
    await ensure_occurrences_generated(series, session)
    await session.refresh(series)
    return series


@router.patch(
    "/series/{series_id}",
    response_model=SeriesResponse,
    summary="Update a series (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Series not found"},
    },
)
async def update_series(
    series_id: uuid.UUID,
    body: SeriesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    series, member = await _get_series_member(series_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(series, field, value)

    await session.commit()
    await session.refresh(series)
    return series


@router.get(
    "/series/{series_id}/occurrences",
    response_model=list[OccurrenceResponse],
    summary="List occurrences for a series",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Series not found"},
    },
)
async def list_occurrences(
    series_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    series, _ = await _get_series_member(series_id, current_user, session)
    await ensure_occurrences_generated(series, session)

    result = await session.execute(
        select(NightOccurrence)
        .where(NightOccurrence.series_id == series_id)
        .order_by(NightOccurrence.occurrence_date)
    )
    return list(result.scalars().all())
