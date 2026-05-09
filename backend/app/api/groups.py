import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.group import Group, GroupInvite, GroupMember
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    InviteCreate,
    InvitePreview,
    InviteResponse,
    MemberResponse,
)
from app.services.email import send_group_invite_email

router = APIRouter(prefix="/groups", tags=["groups"])
invites_router = APIRouter(prefix="/invites", tags=["groups"])


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-")


async def _unique_slug(base: str, session: AsyncSession) -> str:
    slug = base
    for _ in range(5):
        existing = await session.execute(select(Group).where(Group.slug == slug))
        if not existing.scalar_one_or_none():
            return slug
        slug = f"{base}-{secrets.token_hex(3)}"
    return f"{base}-{secrets.token_hex(6)}"


async def _get_group_and_member(
    group_id: uuid.UUID,
    session: AsyncSession,
    user: User,
) -> tuple[Group, GroupMember]:
    group = await session.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    member = await session.get(GroupMember, (group_id, user.id))
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    return group, member


def _require_organiser(member: GroupMember) -> None:
    if member.role != "organiser":
        raise HTTPException(status_code=403, detail="Organiser access required")


# ── groups ──────────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_201_CREATED, response_model=GroupResponse)
async def create_group(
    body: GroupCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    base_slug = body.slug or _slugify(body.name) or "group"
    slug = await _unique_slug(base_slug, session)

    group = Group(
        name=body.name,
        description=body.description,
        slug=slug,
        owner_id=current_user.id,
        is_public=body.is_public,
    )
    session.add(group)
    await session.flush()

    member = GroupMember(group_id=group.id, user_id=current_user.id, role="organiser")
    session.add(member)
    await session.commit()
    await session.refresh(group)

    resp = GroupResponse.model_validate(group)
    resp.member_count = 1
    resp.my_role = "organiser"
    return resp


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Group, GroupMember)
        .join(GroupMember, Group.id == GroupMember.group_id)
        .where(GroupMember.user_id == current_user.id)
        .order_by(Group.created_at.desc())
    )
    rows = result.all()

    groups = []
    for group, member in rows:
        count_result = await session.execute(
            select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group.id)
        )
        resp = GroupResponse.model_validate(group)
        resp.member_count = count_result.scalar_one()
        resp.my_role = member.role
        groups.append(resp)
    return groups


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group, member = await _get_group_and_member(group_id, session, current_user)
    count_result = await session.execute(
        select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group_id)
    )
    resp = GroupResponse.model_validate(group)
    resp.member_count = count_result.scalar_one()
    resp.my_role = member.role
    return resp


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    body: GroupUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group, member = await _get_group_and_member(group_id, session, current_user)
    _require_organiser(member)

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description
    if body.is_public is not None:
        group.is_public = body.is_public

    await session.commit()
    await session.refresh(group)
    resp = GroupResponse.model_validate(group)
    resp.my_role = member.role
    return resp


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group, _ = await _get_group_and_member(group_id, session, current_user)
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this group")
    await session.delete(group)
    await session.commit()


# ── members ──────────────────────────────────────────────────────────────────


@router.get("/{group_id}/members", response_model=list[MemberResponse])
async def list_members(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _get_group_and_member(group_id, session, current_user)
    result = await session.execute(
        select(GroupMember, User)
        .join(User, GroupMember.user_id == User.id)
        .where(GroupMember.group_id == group_id)
        .order_by(GroupMember.joined_at)
    )
    members = []
    for gm, user in result.all():
        resp = MemberResponse.model_validate(gm)
        resp.username = user.username
        resp.display_name = user.display_name
        members.append(resp)
    return members


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group, member = await _get_group_and_member(group_id, session, current_user)
    _require_organiser(member)

    if user_id == group.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove the group owner")

    target = await session.get(GroupMember, (group_id, user_id))
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    await session.delete(target)
    await session.commit()


# ── invites ──────────────────────────────────────────────────────────────────


@router.post("/{group_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    group_id: uuid.UUID,
    body: InviteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group, member = await _get_group_and_member(group_id, session, current_user)
    _require_organiser(member)

    expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    invite = GroupInvite(
        group_id=group_id,
        email=body.email,
        role=body.role,
        expires_at=expires_at,
        created_by=current_user.id,
    )
    session.add(invite)
    await session.commit()
    await session.refresh(invite)

    if body.email:
        from app.config import settings

        invite_url = f"{settings.frontend_url}/invites/{invite.token}"
        send_group_invite_email(body.email, group.name, current_user.username, invite_url)

    return invite


@router.get("/{group_id}/invites", response_model=list[InviteResponse])
async def list_invites(
    group_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _, member = await _get_group_and_member(group_id, session, current_user)
    _require_organiser(member)

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(GroupInvite)
        .where(GroupInvite.group_id == group_id)
        .where(GroupInvite.used_at.is_(None))
        .where(GroupInvite.expires_at > now)
        .order_by(GroupInvite.created_at.desc())
    )
    return list(result.scalars().all())


# ── invite accept (no group_id in path) ───────────────────────────────────────


@invites_router.get("/{token}", response_model=InvitePreview)
async def preview_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    invite = await _resolve_invite(token, session)
    group = await session.get(Group, invite.group_id)
    inviter = await session.get(User, invite.created_by)
    return InvitePreview(
        group_id=group.id,
        group_name=group.name,
        group_description=group.description,
        role=invite.role,
        inviter_username=inviter.username,
    )


@invites_router.post("/{token}/accept", status_code=status.HTTP_200_OK)
async def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(GroupInvite).where(GroupInvite.token == token))
    invite = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not invite or invite.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=404, detail="Invite not found or expired")

    existing = await session.get(GroupMember, (invite.group_id, current_user.id))
    if existing:
        return {"message": "Already a member of this group"}

    if invite.used_at:
        raise HTTPException(status_code=410, detail="Invite already used")

    member = GroupMember(
        group_id=invite.group_id,
        user_id=current_user.id,
        role=invite.role,
        invited_by=invite.created_by,
    )
    session.add(member)
    invite.used_at = datetime.now(timezone.utc)
    await session.commit()
    return {"message": "Joined group successfully", "role": invite.role}


async def _resolve_invite(token: str, session: AsyncSession) -> GroupInvite:
    result = await session.execute(select(GroupInvite).where(GroupInvite.token == token))
    invite = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if not invite or invite.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    if invite.used_at:
        raise HTTPException(status_code=410, detail="Invite already used")
    return invite
