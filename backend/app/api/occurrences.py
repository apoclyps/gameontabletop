import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupMember
from app.models.scheduler import NightOccurrence, NightSeries, Rsvp
from app.models.user import User
from app.schemas.scheduler import OccurrenceCreate, OccurrenceResponse, OccurrenceUpdate, RsvpCreate, RsvpOut

router = APIRouter(tags=["occurrences"])


@router.get("/me/occurrences")
async def list_my_upcoming_occurrences(
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
    result = await session.execute(
        select(NightOccurrence, NightSeries, Group)
        .join(NightSeries, NightOccurrence.series_id == NightSeries.id)
        .join(Group, NightSeries.group_id == Group.id)
        .where(NightSeries.group_id.in_(group_ids))
        .where(NightOccurrence.occurrence_date >= today)
        .where(NightOccurrence.status != "cancelled")
        .order_by(NightOccurrence.occurrence_date.asc(), NightOccurrence.start_time.asc())
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


@router.get("/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
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


@router.patch("/occurrences/{occurrence_id}", response_model=OccurrenceResponse)
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


@router.post("/occurrences/{occurrence_id}/rsvp", response_model=RsvpOut)
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


@router.get("/occurrences/{occurrence_id}/rsvps", response_model=list[RsvpOut])
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


async def _rsvp_counts(occurrence_id: uuid.UUID, session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {"yes": 0, "no": 0, "maybe": 0}
    result = await session.execute(select(Rsvp).where(Rsvp.occurrence_id == occurrence_id))
    for rsvp in result.scalars().all():
        if rsvp.response in counts:
            counts[rsvp.response] += 1
    return counts
