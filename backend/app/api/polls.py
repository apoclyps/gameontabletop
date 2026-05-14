import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupMember
from app.models.scheduler import (
    AvailabilityPoll,
    GuestToken,
    NightOccurrence,
    NightSeries,
    PollOption,
    PollResponse,
)
from app.models.user import User
from app.schemas.scheduler import (
    GuestTokenOut,
    OptionResponse,
    PollCreate,
    PollOptionCreate,
    PollOptionOut,
    PollOut,
    PollResolve,
    PollRespond,
)
from app.services.email import send_poll_created_email, send_poll_resolved_email

router = APIRouter(tags=["polls"])


async def _get_poll_and_member(
    poll_id: uuid.UUID, user: User, session: AsyncSession
) -> tuple[AvailabilityPoll, NightSeries, GroupMember]:
    poll = await session.get(AvailabilityPoll, poll_id)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    series = await session.get(NightSeries, poll.series_id)
    member = await session.get(GroupMember, (series.group_id, user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return poll, series, member


async def _build_poll_out(
    poll: AvailabilityPoll,
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
) -> PollOut:
    opts_result = await session.execute(
        select(PollOption)
        .where(PollOption.poll_id == poll.id)
        .order_by(
            PollOption.display_order, PollOption.proposed_date, PollOption.start_time
        )
    )
    options = list(opts_result.scalars().all())

    responses_result = await session.execute(
        select(PollResponse).where(PollResponse.poll_id == poll.id)
    )
    all_responses = list(responses_result.scalars().all())

    option_outs = []
    my_responses: dict[str, str] = {}

    for opt in options:
        counts: dict[str, int] = {"yes": 0, "no": 0, "maybe": 0}
        for r in all_responses:
            if r.option_id == opt.id and r.response in counts:
                counts[r.response] += 1
            if user_id and r.option_id == opt.id and r.user_id == user_id:
                my_responses[str(opt.id)] = r.response
        option_outs.append(
            PollOptionOut(
                id=opt.id,
                poll_id=opt.poll_id,
                proposed_date=opt.proposed_date,
                start_time=opt.start_time,
                end_time=opt.end_time,
                location_id=opt.location_id,
                display_order=opt.display_order,
                response_counts=counts,
            )
        )

    out = PollOut.model_validate(poll)
    out.options = option_outs
    out.my_responses = my_responses
    return out


@router.post(
    "/series/{series_id}/polls",
    response_model=PollOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an availability poll for a series (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Series not found"},
    },
)
async def create_poll(
    series_id: uuid.UUID,
    body: PollCreate,
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

    poll = AvailabilityPoll(
        series_id=series_id,
        title=body.title,
        description=body.description,
        deadline=body.deadline,
        created_by=current_user.id,
    )
    session.add(poll)
    await session.flush()

    for i, opt_data in enumerate(body.options):
        opt = PollOption(
            poll_id=poll.id,
            display_order=opt_data.display_order or i,
            **opt_data.model_dump(exclude={"display_order"}),
        )
        session.add(opt)

    await session.commit()
    await session.refresh(poll)

    group = await session.get(Group, series.group_id)
    members_result = await session.execute(
        select(User)
        .join(GroupMember, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == series.group_id)
    )
    poll_url = f"{settings.frontend_url}/polls/{poll.id}"
    for user in members_result.scalars().all():
        if user.id != current_user.id:
            send_poll_created_email(
                user.email, group.name, series.title, body.title, poll_url
            )

    return await _build_poll_out(poll, session, current_user.id)


@router.get(
    "/series/{series_id}/polls",
    response_model=list[PollOut],
    summary="List polls for a series",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Series not found"},
    },
)
async def list_polls(
    series_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    series = await session.get(NightSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    member = await session.get(GroupMember, (series.group_id, current_user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")

    result = await session.execute(
        select(AvailabilityPoll)
        .where(AvailabilityPoll.series_id == series_id)
        .order_by(AvailabilityPoll.created_at.desc())
    )
    polls = list(result.scalars().all())
    return [await _build_poll_out(p, session, current_user.id) for p in polls]


@router.get(
    "/polls/{poll_id}",
    response_model=PollOut,
    summary="Get a poll with options and response counts",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Poll not found"},
    },
)
async def get_poll(
    poll_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, _, _ = await _get_poll_and_member(poll_id, current_user, session)
    return await _build_poll_out(poll, session, current_user.id)


@router.post(
    "/polls/{poll_id}/options",
    response_model=PollOptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a date option to a poll (organiser only)",
    responses={
        400: {"description": "Poll is not open"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Poll not found"},
    },
)
async def add_poll_option(
    poll_id: uuid.UUID,
    body: PollOptionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, _, member = await _get_poll_and_member(poll_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")
    if poll.status != "open":
        raise HTTPException(
            status_code=400, detail="Cannot add options to a closed or resolved poll"
        )

    opt = PollOption(poll_id=poll_id, **body.model_dump())
    session.add(opt)
    await session.commit()
    await session.refresh(opt)
    return PollOptionOut(
        id=opt.id,
        poll_id=opt.poll_id,
        proposed_date=opt.proposed_date,
        start_time=opt.start_time,
        end_time=opt.end_time,
        location_id=opt.location_id,
        display_order=opt.display_order,
        response_counts={"yes": 0, "no": 0, "maybe": 0},
    )


@router.delete(
    "/polls/{poll_id}/options/{option_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a date option from a poll (organiser only)",
    responses={
        400: {"description": "Poll is not open"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Poll or option not found"},
    },
)
async def remove_poll_option(
    poll_id: uuid.UUID,
    option_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, _, member = await _get_poll_and_member(poll_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")
    if poll.status != "open":
        raise HTTPException(
            status_code=400, detail="Cannot modify a closed or resolved poll"
        )

    opt = await session.get(PollOption, option_id)
    if not opt or opt.poll_id != poll_id:
        raise HTTPException(status_code=404, detail="Option not found")
    await session.delete(opt)
    await session.commit()


@router.post(
    "/polls/{poll_id}/respond",
    response_model=PollOut,
    summary="Submit or update availability responses for a poll",
    responses={
        400: {"description": "Poll is not open"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not a member"},
        404: {"description": "Poll not found"},
    },
)
async def respond_to_poll(
    poll_id: uuid.UUID,
    body: PollRespond,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, _, _ = await _get_poll_and_member(poll_id, current_user, session)
    if poll.status != "open":
        raise HTTPException(status_code=400, detail="Poll is not open for responses")

    await _upsert_responses(poll_id, body.responses, session, user_id=current_user.id)
    await session.commit()
    return await _build_poll_out(poll, session, current_user.id)


@router.post(
    "/polls/{poll_id}/resolve",
    response_model=PollOut,
    summary="Resolve a poll by picking the winning date and creating an occurrence (organiser only)",
    responses={
        400: {"description": "Poll already resolved or invalid option"},
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Poll not found"},
    },
)
async def resolve_poll(
    poll_id: uuid.UUID,
    body: PollResolve,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, series, member = await _get_poll_and_member(poll_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")
    if poll.status == "resolved":
        raise HTTPException(status_code=400, detail="Poll already resolved")

    chosen = await session.get(PollOption, body.chosen_option_id)
    if not chosen or chosen.poll_id != poll_id:
        raise HTTPException(
            status_code=400, detail="Option does not belong to this poll"
        )

    poll.status = "resolved"
    poll.chosen_option_id = chosen.id

    occ = NightOccurrence(
        series_id=series.id,
        occurrence_date=chosen.proposed_date,
        start_time=chosen.start_time,
        end_time=chosen.end_time,
        location_id=chosen.location_id,
        is_auto_generated=False,
    )
    session.add(occ)

    if not series.series_start_date:
        series.series_start_date = chosen.proposed_date

    await session.commit()
    await session.refresh(poll)
    await session.refresh(occ)

    members_result = await session.execute(
        select(User)
        .join(GroupMember, User.id == GroupMember.user_id)
        .where(GroupMember.group_id == series.group_id)
    )
    occ_url = f"{settings.frontend_url}/occurrences/{occ.id}"
    chosen_date_str = chosen.proposed_date.strftime("%A, %d %B %Y")
    chosen_time_str = chosen.start_time.strftime("%H:%M")
    for user in members_result.scalars().all():
        send_poll_resolved_email(
            user.email, series.title, chosen_date_str, chosen_time_str, occ_url
        )

    return await _build_poll_out(poll, session, current_user.id)


@router.post(
    "/polls/{poll_id}/guest-link",
    response_model=GuestTokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a guest link for unauthenticated poll responses (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Poll not found"},
    },
)
async def create_poll_guest_link(
    poll_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    poll, series, member = await _get_poll_and_member(poll_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    gt = GuestToken(
        token=raw_token,
        series_id=series.id,
        poll_id=poll.id,
        expires_at=expires_at,
    )
    session.add(gt)
    await session.commit()

    url = f"{settings.frontend_url}/poll-respond/{raw_token}"
    return GuestTokenOut(token=raw_token, url=url, expires_at=expires_at)


@router.post(
    "/occurrences/{occurrence_id}/guest-link",
    response_model=GuestTokenOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a guest RSVP link for an occurrence (organiser only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Not an organiser"},
        404: {"description": "Occurrence not found"},
    },
)
async def create_occurrence_guest_link(
    occurrence_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    occ = await session.get(NightOccurrence, occurrence_id)
    if not occ:
        raise HTTPException(status_code=404, detail="Occurrence not found")
    series = await session.get(NightSeries, occ.series_id)
    member = await session.get(GroupMember, (series.group_id, current_user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    gt = GuestToken(
        token=raw_token,
        series_id=series.id,
        occurrence_id=occ.id,
        expires_at=expires_at,
    )
    session.add(gt)
    await session.commit()

    url = f"{settings.frontend_url}/rsvp/{raw_token}"
    return GuestTokenOut(token=raw_token, url=url, expires_at=expires_at)


async def _upsert_responses(
    poll_id: uuid.UUID,
    responses: list[OptionResponse],
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    guest_token_id: uuid.UUID | None = None,
    guest_name: str | None = None,
) -> None:
    for item in responses:
        existing = await session.execute(
            select(PollResponse)
            .where(PollResponse.option_id == item.option_id)
            .where(
                PollResponse.user_id == user_id
                if user_id
                else PollResponse.guest_token_id == guest_token_id
            )
        )
        pr = existing.scalar_one_or_none()
        if pr:
            pr.response = item.response
            pr.responded_at = datetime.now(timezone.utc)
        else:
            pr = PollResponse(
                poll_id=poll_id,
                option_id=item.option_id,
                user_id=user_id,
                guest_token_id=guest_token_id,
                guest_name=guest_name,
                response=item.response,
            )
            session.add(pr)
