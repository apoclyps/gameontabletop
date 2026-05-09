import uuid

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    address: str | None = None
    is_virtual: bool = False
    virtual_url: str | None = None
    notes: str | None = None


class LocationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    address: str | None = None
    is_virtual: bool | None = None
    virtual_url: str | None = None
    notes: str | None = None


class LocationResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    name: str
    address: str | None
    is_virtual: bool
    virtual_url: str | None
    notes: str | None

    model_config = {"from_attributes": True}
