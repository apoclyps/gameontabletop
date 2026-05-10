import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.collection import UserGameCollection
from app.models.user import User
from app.schemas.collection import CollectionEntryCreate, CollectionEntryResponse, CollectionEntryUpdate
from app.services.collection import is_friend

router = APIRouter(tags=["collection"])


async def get_optional_user(request: Request, session: AsyncSession = Depends(get_session)):
    """Returns current user or None if not authenticated."""
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ")[1]
        from app.services.auth import decode_token

        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = uuid.UUID(payload["sub"])
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


@router.get("/users/me/collection", response_model=list[CollectionEntryResponse])
async def list_my_collection(
    status: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    query = select(UserGameCollection).where(UserGameCollection.user_id == current_user.id)
    if status is not None:
        query = query.where(UserGameCollection.status == status)
    query = query.order_by(UserGameCollection.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


@router.post(
    "/users/me/collection",
    response_model=CollectionEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_collection(
    body: CollectionEntryCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Check for duplicate bgg_game_id
    if body.bgg_game_id is not None:
        existing = await session.execute(
            select(UserGameCollection).where(
                and_(
                    UserGameCollection.user_id == current_user.id,
                    UserGameCollection.bgg_game_id == body.bgg_game_id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Game with this BGG ID already in your collection",
            )

    entry = UserGameCollection(
        user_id=current_user.id,
        bgg_game_id=body.bgg_game_id,
        game_title=body.game_title,
        game_thumbnail_url=body.game_thumbnail_url,
        min_players=body.min_players,
        max_players=body.max_players,
        complexity=body.complexity,
        status=body.status,
        notes=body.notes,
        source="manual",
        acquired_at=body.acquired_at,
        collection_visible_to=body.collection_visible_to,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.patch("/users/me/collection/{entry_id}", response_model=CollectionEntryResponse)
async def update_collection_entry(
    entry_id: uuid.UUID,
    body: CollectionEntryUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    entry = await session.get(UserGameCollection, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")
    if uuid.UUID(str(entry.user_id)) != current_user.id:
        raise HTTPException(status_code=403, detail="Not your collection entry")

    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(entry, field, value)

    await session.commit()
    await session.refresh(entry)
    return entry


@router.delete("/users/me/collection/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    entry = await session.get(UserGameCollection, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")
    if uuid.UUID(str(entry.user_id)) != current_user.id:
        raise HTTPException(status_code=403, detail="Not your collection entry")

    await session.delete(entry)
    await session.commit()
    return Response(status_code=204)


@router.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "username": user.username,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }


@router.get("/users/{user_id}/collection", response_model=list[CollectionEntryResponse])
async def get_user_collection(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    current_user = await get_optional_user(request, session)

    result = await session.execute(
        select(UserGameCollection)
        .where(UserGameCollection.user_id == user_id)
        .order_by(UserGameCollection.created_at.desc())
    )
    entries = result.scalars().all()

    # Determine if viewer is owner
    viewer_id = current_user.id if current_user else None
    is_owner = viewer_id is not None and uuid.UUID(str(viewer_id)) == user_id

    if is_owner:
        return list(entries)

    # Filter by visibility
    viewer_is_friend = False
    if viewer_id is not None:
        viewer_is_friend = await is_friend(session, viewer_id, user_id)

    visible = []
    for entry in entries:
        vis = entry.collection_visible_to
        if vis == "public":
            visible.append(entry)
        elif vis == "friends" and viewer_is_friend:
            visible.append(entry)
        # "private" and non-friend "friends" entries are excluded

    return visible
