import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.collection import UserGameCollection
from app.models.group import Group
from app.models.scheduler import NightOccurrence, NightSeries, Rsvp
from app.models.user import User
from app.schemas.public import PublicEventDetail, PublicEventItem, PublicProfileResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get(
    "/events",
    response_model=list[PublicEventItem],
    summary="List upcoming public game night events (paginated)",
)
async def list_public_events(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    today = date.today()
    offset = (page - 1) * per_page

    result = await session.execute(
        select(NightOccurrence, NightSeries, Group)
        .join(NightSeries, NightOccurrence.series_id == NightSeries.id)
        .join(Group, NightSeries.group_id == Group.id)
        .where(NightOccurrence.occurrence_date >= today)
        .where(NightOccurrence.status == "scheduled")
        .where(Group.is_public.is_(True))
        .order_by(NightOccurrence.occurrence_date.asc())
        .offset(offset)
        .limit(per_page)
    )
    rows = result.all()

    events = []
    for occ, series, group in rows:
        rsvp_result = await session.execute(
            select(func.count())
            .select_from(Rsvp)
            .where(Rsvp.occurrence_id == occ.id)
            .where(Rsvp.response == "yes")
        )
        events.append(
            {
                "id": str(occ.id),
                "occurrence_date": occ.occurrence_date.isoformat(),
                "start_time": str(occ.start_time),
                "end_time": str(occ.end_time) if occ.end_time else None,
                "group_name": group.name,
                "group_slug": group.slug,
                "series_title": series.title,
                "rsvp_yes_count": rsvp_result.scalar_one(),
            }
        )

    return events


@router.get(
    "/events/{occurrence_id}",
    response_model=PublicEventDetail,
    summary="Get details of a single public event",
    responses={404: {"description": "Event not found or not public"}},
)
async def get_public_event(
    occurrence_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(NightOccurrence, NightSeries, Group)
        .join(NightSeries, NightOccurrence.series_id == NightSeries.id)
        .join(Group, NightSeries.group_id == Group.id)
        .where(NightOccurrence.id == occurrence_id)
        .where(Group.is_public.is_(True))
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    occ, series, group = row

    rsvp_result = await session.execute(
        select(func.count())
        .select_from(Rsvp)
        .where(Rsvp.occurrence_id == occ.id)
        .where(Rsvp.response == "yes")
    )

    return {
        "id": str(occ.id),
        "occurrence_date": occ.occurrence_date.isoformat(),
        "start_time": str(occ.start_time),
        "end_time": str(occ.end_time) if occ.end_time else None,
        "status": occ.status,
        "notes": occ.notes,
        "group_name": group.name,
        "group_slug": group.slug,
        "series_title": series.title,
        "rsvp_yes_count": rsvp_result.scalar_one(),
    }


@router.get(
    "/profile/{username}",
    response_model=PublicProfileResponse,
    summary="Get a user's public profile by username",
    responses={404: {"description": "Profile not found or not public"}},
)
async def get_public_profile(
    username: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not user.profile_public:
        raise HTTPException(status_code=404, detail="Profile not found")

    owned_result = await session.execute(
        select(func.count())
        .select_from(UserGameCollection)
        .where(UserGameCollection.user_id == user.id)
        .where(UserGameCollection.status == "own")
    )
    games_owned = owned_result.scalar_one()

    return {
        "username": user.username,
        "display_name": user.display_name,
        "bio": user.bio,
        "avatar_url": user.avatar_url,
        "member_since": user.created_at.date().isoformat(),
        "stats_public": user.stats_public,
        "stats": {
            "total_games_played": 0,
            "total_plays": 0,
            "games_owned": games_owned if user.stats_public else 0,
        },
    }
