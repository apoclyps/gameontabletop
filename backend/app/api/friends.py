import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.collection import UserFriendship, UserGameCollection
from app.models.group import GroupMember
from app.models.user import User
from app.schemas.collection import (
    FriendGameEntry,
    FriendRequestCreate,
    FriendResponse,
    FriendshipPatch,
)
from app.services.collection import get_friend_ids

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("", response_model=list[FriendResponse])
async def list_friends(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserFriendship).where(
            or_(
                UserFriendship.requester_id == current_user.id,
                UserFriendship.addressee_id == current_user.id,
            ),
            UserFriendship.status == "accepted",
        )
    )
    friendships = result.scalars().all()

    friends = []
    for friendship in friendships:
        friend_id = (
            friendship.addressee_id
            if uuid.UUID(str(friendship.requester_id)) == current_user.id
            else friendship.requester_id
        )
        friend_user = await session.get(User, friend_id)
        if not friend_user:
            continue

        # Count games with status="own" visible to us (public or friends-visible since we're friends)
        count_result = await session.execute(
            select(func.count()).select_from(UserGameCollection).where(
                and_(
                    UserGameCollection.user_id == uuid.UUID(str(friend_id)),
                    UserGameCollection.status == "own",
                    or_(
                        UserGameCollection.collection_visible_to == "public",
                        UserGameCollection.collection_visible_to == "friends",
                    ),
                )
            )
        )
        game_count = count_result.scalar_one()

        friends.append(
            FriendResponse(
                friendship_id=friendship.id,
                user_id=friend_user.id,
                username=friend_user.username,
                display_name=friend_user.display_name,
                avatar_url=friend_user.avatar_url,
                status=friendship.status,
                game_count=game_count,
            )
        )
    return friends


@router.post("/request", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    body: FriendRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Find target user by username
    result = await session.execute(select(User).where(User.username == body.username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=400, detail="User not found")

    if uuid.UUID(str(target.id)) == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")

    # Check for existing friendship/request
    existing_result = await session.execute(
        select(UserFriendship).where(
            or_(
                and_(
                    UserFriendship.requester_id == current_user.id,
                    UserFriendship.addressee_id == uuid.UUID(str(target.id)),
                ),
                and_(
                    UserFriendship.requester_id == uuid.UUID(str(target.id)),
                    UserFriendship.addressee_id == current_user.id,
                ),
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        if existing.status == "blocked":
            raise HTTPException(status_code=400, detail="Cannot send request: blocked")
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="Already friends")
        if existing.status == "pending":
            raise HTTPException(status_code=409, detail="Friend request already pending")
        if existing.status == "declined":
            # Allow re-request by updating status back to pending
            existing.status = "pending"
            existing.requester_id = current_user.id
            existing.addressee_id = uuid.UUID(str(target.id))
            existing.requested_at = datetime.now(timezone.utc)
            existing.responded_at = None
            await session.commit()
            await session.refresh(existing)
            return {"friendship_id": str(existing.id), "status": existing.status}

    friendship = UserFriendship(
        requester_id=current_user.id,
        addressee_id=uuid.UUID(str(target.id)),
        status="pending",
    )
    session.add(friendship)
    await session.commit()
    await session.refresh(friendship)
    return {"friendship_id": str(friendship.id), "status": friendship.status}


@router.get("/requests", response_model=list[FriendResponse])
async def list_friend_requests(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(UserFriendship).where(
            UserFriendship.addressee_id == current_user.id,
            UserFriendship.status == "pending",
        )
    )
    friendships = result.scalars().all()

    requests = []
    for friendship in friendships:
        requester = await session.get(User, friendship.requester_id)
        if not requester:
            continue
        requests.append(
            FriendResponse(
                friendship_id=friendship.id,
                user_id=requester.id,
                username=requester.username,
                display_name=requester.display_name,
                avatar_url=requester.avatar_url,
                status=friendship.status,
                game_count=0,
            )
        )
    return requests


@router.patch("/{friendship_id}", response_model=FriendResponse)
async def patch_friendship(
    friendship_id: uuid.UUID,
    body: FriendshipPatch,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    friendship = await session.get(UserFriendship, friendship_id)
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")

    requester_id = uuid.UUID(str(friendship.requester_id))
    addressee_id = uuid.UUID(str(friendship.addressee_id))

    is_requester = requester_id == current_user.id
    is_addressee = addressee_id == current_user.id

    if not is_requester and not is_addressee:
        raise HTTPException(status_code=403, detail="Not part of this friendship")

    # Only addressee can accept/decline; either can block
    if body.status in ("accepted", "declined") and not is_addressee:
        raise HTTPException(status_code=403, detail="Only the addressee can accept or decline")

    friendship.status = body.status
    friendship.responded_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(friendship)

    # Return info about the other party
    other_id = addressee_id if is_requester else requester_id
    other_user = await session.get(User, other_id)

    return FriendResponse(
        friendship_id=friendship.id,
        user_id=other_user.id,
        username=other_user.username,
        display_name=other_user.display_name,
        avatar_url=other_user.avatar_url,
        status=friendship.status,
        game_count=0,
    )


@router.delete("/{friendship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_friendship(
    friendship_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    friendship = await session.get(UserFriendship, friendship_id)
    if not friendship:
        raise HTTPException(status_code=404, detail="Friendship not found")

    requester_id = uuid.UUID(str(friendship.requester_id))
    addressee_id = uuid.UUID(str(friendship.addressee_id))

    if requester_id != current_user.id and addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not part of this friendship")

    await session.delete(friendship)
    await session.commit()


@router.get("/collection", response_model=list[FriendGameEntry])
async def friends_collection(
    status: str = "own",
    q: str | None = None,
    min_players: int | None = None,
    max_players: int | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    friend_ids = await get_friend_ids(session, current_user.id)
    if not friend_ids:
        return []

    query = select(UserGameCollection, User).join(
        User, UserGameCollection.user_id == User.id
    ).where(
        and_(
            UserGameCollection.user_id.in_([uuid.UUID(str(fid)) for fid in friend_ids]),
            UserGameCollection.status == status,
            UserGameCollection.bgg_game_id.isnot(None),
            or_(
                UserGameCollection.collection_visible_to == "public",
                UserGameCollection.collection_visible_to == "friends",
            ),
        )
    )

    if q:
        query = query.where(UserGameCollection.game_title.ilike(f"%{q}%"))
    if min_players is not None:
        query = query.where(
            or_(
                UserGameCollection.min_players.is_(None),
                UserGameCollection.min_players <= min_players,
            )
        )
    if max_players is not None:
        query = query.where(
            or_(
                UserGameCollection.max_players.is_(None),
                UserGameCollection.max_players >= max_players,
            )
        )

    result = await session.execute(query)
    rows = result.all()

    # Group by bgg_game_id
    grouped: dict[int, dict] = {}
    for entry, user in rows:
        bgg_id = entry.bgg_game_id
        if bgg_id not in grouped:
            grouped[bgg_id] = {
                "bgg_game_id": bgg_id,
                "game_title": entry.game_title,
                "game_thumbnail_url": entry.game_thumbnail_url,
                "min_players": entry.min_players,
                "max_players": entry.max_players,
                "complexity": float(entry.complexity) if entry.complexity is not None else None,
                "owners": [],
            }
        grouped[bgg_id]["owners"].append(
            {
                "user_id": str(user.id),
                "username": user.username,
                "display_name": user.display_name,
            }
        )

    return [FriendGameEntry(**data) for data in grouped.values()]


@router.get("/suggestions", response_model=list[dict])
async def friend_suggestions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Get current friend IDs
    friend_ids = await get_friend_ids(session, current_user.id)
    friend_id_set = {uuid.UUID(str(fid)) for fid in friend_ids}

    # Get blocked user IDs
    blocked_result = await session.execute(
        select(UserFriendship).where(
            or_(
                UserFriendship.requester_id == current_user.id,
                UserFriendship.addressee_id == current_user.id,
            ),
            UserFriendship.status == "blocked",
        )
    )
    blocked_friendships = blocked_result.scalars().all()
    blocked_ids = set()
    for f in blocked_friendships:
        blocked_ids.add(uuid.UUID(str(f.requester_id)))
        blocked_ids.add(uuid.UUID(str(f.addressee_id)))
    blocked_ids.discard(current_user.id)

    # Find group co-members
    my_groups_result = await session.execute(
        select(GroupMember.group_id).where(GroupMember.user_id == current_user.id)
    )
    my_group_ids = [row[0] for row in my_groups_result.all()]

    if not my_group_ids:
        return []

    co_members_result = await session.execute(
        select(GroupMember.user_id).where(
            and_(
                GroupMember.group_id.in_(my_group_ids),
                GroupMember.user_id != current_user.id,
            )
        ).distinct()
    )
    co_member_ids = [row[0] for row in co_members_result.all()]

    suggestions = []
    for uid in co_member_ids:
        uid_val = uuid.UUID(str(uid))
        if uid_val in friend_id_set or uid_val in blocked_ids:
            continue
        user = await session.get(User, uid_val)
        if user:
            suggestions.append(
                {
                    "user_id": str(user.id),
                    "username": user.username,
                    "display_name": user.display_name,
                    "avatar_url": user.avatar_url,
                }
            )
        if len(suggestions) >= 5:
            break

    return suggestions
