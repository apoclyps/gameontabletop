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


PollStatus = Literal["open", "closed", "resolved"]
PollResponseChoice = Literal["yes", "no", "maybe"]


class PollOptionCreate(BaseModel):
    proposed_date: date
    start_time: time
    end_time: time | None = None
    location_id: uuid.UUID | None = None
    display_order: int = Field(default=0, ge=0)


class PollOptionOut(BaseModel):
    id: uuid.UUID
    poll_id: uuid.UUID
    proposed_date: date
    start_time: time
    end_time: time | None
    location_id: uuid.UUID | None
    display_order: int
    response_counts: dict[str, int] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class PollCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    options: list[PollOptionCreate] = Field(default_factory=list)


class PollOut(BaseModel):
    id: uuid.UUID
    series_id: uuid.UUID
    title: str
    description: str | None
    deadline: datetime | None
    status: str
    chosen_option_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    options: list[PollOptionOut] = Field(default_factory=list)
    my_responses: dict[str, str] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class OptionResponse(BaseModel):
    option_id: uuid.UUID
    response: PollResponseChoice


class PollRespond(BaseModel):
    responses: list[OptionResponse]


class PollResolve(BaseModel):
    chosen_option_id: uuid.UUID


class GuestTokenOut(BaseModel):
    token: str
    url: str
    expires_at: datetime


class GuestRsvpCreate(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=100)
    response: RsvpChoice
    note: str | None = None


class GuestPollRespond(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=100)
    responses: list[OptionResponse]


class GuestContext(BaseModel):
    type: str
    token: str
    guest_name: str | None = None
    # poll fields
    poll_id: uuid.UUID | None = None
    poll_title: str | None = None
    series_title: str | None = None
    group_name: str | None = None
    options: list[PollOptionOut] = Field(default_factory=list)
    my_responses: dict[str, str] = Field(default_factory=dict)
    # rsvp fields
    occurrence_id: uuid.UUID | None = None
    occurrence_date: date | None = None
    occurrence_start_time: time | None = None


class OccurrencePhotoOut(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    uploaded_by: uuid.UUID
    photo_url: str
    caption: str | None
    created_at: datetime
    username: str | None = None

    model_config = {"from_attributes": True}


class RsvpCreate(BaseModel):
    response: RsvpChoice
    note: str | None = None


class RsvpOut(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    user_id: uuid.UUID | None
    response: str
    note: str | None
    responded_at: datetime
    username: str | None = None

    model_config = {"from_attributes": True}
