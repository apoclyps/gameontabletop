import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminUserItem(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    display_name: str | None
    is_active: bool
    is_verified: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminRoleUpdate(BaseModel):
    is_admin: bool


class AdminUsersPage(BaseModel):
    users: list[AdminUserItem]
    total: int
    page: int
    page_size: int
