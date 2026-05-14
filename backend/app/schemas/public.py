from pydantic import BaseModel


class PublicEventItem(BaseModel):
    id: str
    occurrence_date: str
    start_time: str
    end_time: str | None
    group_name: str
    group_slug: str
    series_title: str
    rsvp_yes_count: int


class PublicEventDetail(BaseModel):
    id: str
    occurrence_date: str
    start_time: str
    end_time: str | None
    status: str
    notes: str | None
    group_name: str
    group_slug: str
    series_title: str
    rsvp_yes_count: int


class PublicProfileStats(BaseModel):
    total_games_played: int
    total_plays: int
    games_owned: int


class PublicProfileResponse(BaseModel):
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    member_since: str
    stats_public: bool
    stats: PublicProfileStats
