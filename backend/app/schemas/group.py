import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    slug: str | None = Field(None, max_length=100, pattern=r"^[a-z0-9-]+$")
    is_public: bool = False
    seat_size: int | None = Field(None, ge=1, le=100)


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_public: bool | None = None
    seat_size: int | None = Field(None, ge=1, le=100)


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    slug: str
    owner_id: uuid.UUID
    is_public: bool
    seat_size: int | None
    created_at: datetime
    member_count: int | None = None
    my_role: str | None = None

    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    group_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    username: str | None = None
    display_name: str | None = None

    model_config = {"from_attributes": True}


class InviteCreate(BaseModel):
    email: str | None = None
    role: Literal["organiser", "member"] = "member"
    expires_in_days: int = Field(7, ge=1, le=30)


class InviteResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    email: str | None
    token: str
    role: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvitePreview(BaseModel):
    group_id: uuid.UUID
    group_name: str
    group_description: str | None
    role: str
    inviter_username: str
