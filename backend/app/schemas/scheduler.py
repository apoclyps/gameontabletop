import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

RecurrenceType = Literal["once", "weekly", "biweekly", "monthly", "custom"]
SeriesStatus = Literal["active", "on_hold", "cancelled", "completed"]
OccurrenceStatus = Literal["scheduled", "postponed", "cancelled"]
RsvpChoice = Literal["yes", "no", "maybe"]


class SeriesCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    recurrence: RecurrenceType
    default_day_of_week: int | None = Field(None, ge=0, le=6)
    default_start_time: time | None = None
    default_duration_minutes: int | None = Field(None, ge=15, le=1440)
    default_location_id: uuid.UUID | None = None
    series_start_date: date | None = None
    series_end_date: date | None = None


class SeriesUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: SeriesStatus | None = None
    default_start_time: time | None = None
    default_duration_minutes: int | None = Field(None, ge=15, le=1440)
    default_location_id: uuid.UUID | None = None
    series_end_date: date | None = None


class SeriesResponse(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    title: str
    description: str | None
    status: str
    recurrence: str
    default_day_of_week: int | None
    default_start_time: time | None
    default_duration_minutes: int | None
    default_location_id: uuid.UUID | None
    series_start_date: date | None
    series_end_date: date | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OccurrenceCreate(BaseModel):
    occurrence_date: date
    start_time: time
    end_time: time | None = None
    location_id: uuid.UUID | None = None
    title: str | None = None
    notes: str | None = None
    rsvp_deadline: datetime | None = None


class OccurrenceUpdate(BaseModel):
    status: OccurrenceStatus | None = None
    occurrence_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    location_id: uuid.UUID | None = None
    title: str | None = None
    notes: str | None = None
    rsvp_deadline: datetime | None = None
    postponed_from_date: date | None = None


class OccurrenceResponse(BaseModel):
    id: uuid.UUID
    series_id: uuid.UUID
    title: str | None
    occurrence_date: date
    start_time: time
    end_time: time | None
    location_id: uuid.UUID | None
    status: str
    rsvp_deadline: datetime | None
    notes: str | None
    postponed_from_date: date | None
    is_auto_generated: bool
    created_at: datetime
    updated_at: datetime
    rsvp_counts: dict[str, int] | None = None

    model_config = {"from_attributes": True}


class RsvpCreate(BaseModel):
    response: RsvpChoice
    note: str | None = None


class RsvpOut(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    user_id: uuid.UUID
    response: str
    note: str | None
    responded_at: datetime
    username: str | None = None

    model_config = {"from_attributes": True}
