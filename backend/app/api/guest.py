from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.group import Group
from app.models.scheduler import (
    AvailabilityPoll,
    GuestToken,
    NightOccurrence,
    NightSeries,
    PollOption,
    PollResponse,
    Rsvp,
)
from app.schemas.common import MessageResponse
from app.schemas.scheduler import (
    GuestContext,
    GuestPollRespond,
    GuestRsvpCreate,
    PollOptionOut,
    RsvpOut,
)

router = APIRouter(prefix="/guest", tags=["guest"])


async def _resolve_token(token: str, session: AsyncSession) -> GuestToken:
    result = await session.execute(select(GuestToken).where(GuestToken.token == token))
    gt = result.scalar_one_or_none()
    if not gt:
        raise HTTPException(status_code=404, detail="Guest link not found")
    if gt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Guest link has expired")
    return gt


@router.get(
    "/{token}",
    response_model=GuestContext,
    summary="Resolve a guest token and return context (poll or RSVP)",
    responses={
        400: {"description": "Invalid guest token scope"},
        404: {"description": "Guest link not found"},
        410: {"description": "Guest link has expired"},
    },
)
async def resolve_guest_token(token: str, session: AsyncSession = Depends(get_session)):
    gt = await _resolve_token(token, session)

    if gt.poll_id:
        poll = await session.get(AvailabilityPoll, gt.poll_id)
        series = await session.get(NightSeries, poll.series_id)
        group = await session.get(Group, series.group_id)

        opts_result = await session.execute(
            select(PollOption)
            .where(PollOption.poll_id == poll.id)
            .order_by(PollOption.display_order, PollOption.proposed_date)
        )
        options = list(opts_result.scalars().all())

        responses_result = await session.execute(
            select(PollResponse)
            .where(PollResponse.poll_id == poll.id)
            .where(PollResponse.guest_token_id == gt.id)
        )
        my_responses = {str(r.option_id): r.response for r in responses_result.scalars().all()}

        counts_result = await session.execute(
            select(PollResponse).where(PollResponse.poll_id == poll.id)
        )
        all_responses = list(counts_result.scalars().all())

        option_outs = []
        for opt in options:
            counts: dict[str, int] = {"yes": 0, "no": 0, "maybe": 0}
            for r in all_responses:
                if r.option_id == opt.id and r.response in counts:
                    counts[r.response] += 1
            option_outs.append(PollOptionOut(
                id=opt.id, poll_id=opt.poll_id, proposed_date=opt.proposed_date,
                start_time=opt.start_time, end_time=opt.end_time,
                location_id=opt.location_id, display_order=opt.display_order,
                response_counts=counts,
            ))

        return GuestContext(
            type="poll",
            token=token,
            guest_name=gt.guest_name,
            poll_id=poll.id,
            poll_title=poll.title,
            series_title=series.title,
            group_name=group.name,
            options=option_outs,
            my_responses=my_responses,
        )

    elif gt.occurrence_id:
        occ = await session.get(NightOccurrence, gt.occurrence_id)
        series = await session.get(NightSeries, occ.series_id)
        group = await session.get(Group, series.group_id)
        return GuestContext(
            type="rsvp",
            token=token,
            guest_name=gt.guest_name,
            occurrence_id=occ.id,
            occurrence_date=occ.occurrence_date,
            occurrence_start_time=occ.start_time,
            group_name=group.name,
            series_title=series.title,
        )

    raise HTTPException(status_code=400, detail="Invalid guest token scope")


@router.post(
    "/{token}/rsvp",
    response_model=RsvpOut,
    summary="Submit or update a guest RSVP",
    responses={
        400: {"description": "Token is not for an RSVP or occurrence is cancelled"},
        404: {"description": "Guest link not found"},
        410: {"description": "Guest link has expired"},
    },
)
async def guest_rsvp(
    token: str,
    body: GuestRsvpCreate,
    session: AsyncSession = Depends(get_session),
):
    gt = await _resolve_token(token, session)
    if not gt.occurrence_id:
        raise HTTPException(status_code=400, detail="This link is not for an RSVP")

    occ = await session.get(NightOccurrence, gt.occurrence_id)
    if occ.status == "cancelled":
        raise HTTPException(status_code=400, detail="This occurrence has been cancelled")

    # Update guest_name on token
    gt.guest_name = body.guest_name

    # Upsert RSVP keyed on (occurrence_id, guest_token_id)
    result = await session.execute(
        select(Rsvp)
        .where(Rsvp.occurrence_id == gt.occurrence_id)
        .where(Rsvp.guest_token_id == gt.id)
    )
    rsvp = result.scalar_one_or_none()
    if rsvp:
        rsvp.response = body.response
        rsvp.note = body.note
    else:
        rsvp = Rsvp(
            occurrence_id=gt.occurrence_id,
            guest_token_id=gt.id,
            guest_name=body.guest_name,
            response=body.response,
            note=body.note,
        )
        session.add(rsvp)

    await session.commit()
    await session.refresh(rsvp)
    out = RsvpOut.model_validate(rsvp)
    out.username = body.guest_name
    return out


@router.post(
    "/{token}/poll",
    response_model=MessageResponse,
    summary="Submit or update a guest poll response",
    responses={
        400: {"description": "Token is not for a poll or poll is not open"},
        404: {"description": "Guest link not found"},
        410: {"description": "Guest link has expired"},
    },
)
async def guest_poll_respond(
    token: str,
    body: GuestPollRespond,
    session: AsyncSession = Depends(get_session),
):
    gt = await _resolve_token(token, session)
    if not gt.poll_id:
        raise HTTPException(status_code=400, detail="This link is not for a poll")

    poll = await session.get(AvailabilityPoll, gt.poll_id)
    if poll.status != "open":
        raise HTTPException(status_code=400, detail="Poll is not open for responses")

    gt.guest_name = body.guest_name

    from app.api.polls import _upsert_responses
    await _upsert_responses(
        gt.poll_id, body.responses, session,
        guest_token_id=gt.id, guest_name=body.guest_name,
    )
    await session.commit()
    return {"message": "Response recorded"}
