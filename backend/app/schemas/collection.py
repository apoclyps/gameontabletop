import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

CollectionStatus = Literal["own", "wishlist", "want_to_play", "previously_owned"]
CollectionSource = Literal["bgg_sync", "manual"]
CollectionVisibility = Literal["public", "friends", "private"]
FriendshipStatus = Literal["pending", "accepted", "declined", "blocked"]


class CollectionEntryCreate(BaseModel):
    game_title: str
    bgg_game_id: int | None = None
    game_thumbnail_url: str | None = None
    min_players: int | None = None
    max_players: int | None = None
    complexity: float | None = None
    status: CollectionStatus = "own"
    notes: str | None = None
    acquired_at: date | None = None
    collection_visible_to: CollectionVisibility = "friends"


class CollectionEntryUpdate(BaseModel):
    status: CollectionStatus | None = None
    notes: str | None = None
    collection_visible_to: CollectionVisibility | None = None
    acquired_at: date | None = None


class CollectionEntryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    bgg_game_id: int | None
    game_title: str
    game_thumbnail_url: str | None
    min_players: int | None
    max_players: int | None
    complexity: float | None
    status: str
    notes: str | None
    source: str
    acquired_at: date | None
    collection_visible_to: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FriendRequestCreate(BaseModel):
    username: str  # find by username


class FriendshipPatch(BaseModel):
    status: Literal["accepted", "declined", "blocked"]


class FriendResponse(BaseModel):
    friendship_id: uuid.UUID
    user_id: uuid.UUID
    username: str
    display_name: str | None
    avatar_url: str | None
    status: str
    game_count: int = 0


class FriendGameEntry(BaseModel):
    bgg_game_id: int
    game_title: str
    game_thumbnail_url: str | None
    min_players: int | None
    max_players: int | None
    complexity: float | None
    owners: list[dict]  # [{user_id, username, display_name}]


class FriendRequestResponse(BaseModel):
    friendship_id: str
    status: str


class FriendInviteResponse(BaseModel):
    token: str
    url: str


class FriendInvitePreview(BaseModel):
    inviter_id: str
    inviter_username: str
    inviter_display_name: str | None
    inviter_avatar_url: str | None


class UserPublicProfileResponse(BaseModel):
    id: str
    username: str
    display_name: str | None
    avatar_url: str | None
