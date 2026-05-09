import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupMember
from app.models.location import Location
from app.models.user import User
from app.schemas.location import LocationCreate, LocationResponse, LocationUpdate

router = APIRouter(tags=["locations"])


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


@router.get("/groups/{group_id}/locations", response_model=list[LocationResponse])
async def list_locations(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_group_member(group_id, current_user, session)
    result = await session.execute(
        select(Location).where(Location.group_id == group_id).order_by(Location.name)
    )
    return list(result.scalars().all())


@router.post(
    "/groups/{group_id}/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_location(
    group_id: uuid.UUID,
    body: LocationCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _, member = await _get_group_member(group_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    location = Location(group_id=group_id, **body.model_dump())
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location


@router.patch("/locations/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: uuid.UUID,
    body: LocationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    location = await session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    _, member = await _get_group_member(location.group_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(location, field, value)

    await session.commit()
    await session.refresh(location)
    return location


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    location = await session.get(Location, location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    _, member = await _get_group_member(location.group_id, current_user, session)
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")

    await session.delete(location)
    await session.commit()
