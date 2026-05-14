from pydantic import BaseModel


class BGGGameResponse(BaseModel):
    bgg_id: int
    title: str | None
    thumbnail: str | None
    image: str | None
    year_published: int | None
    min_players: int | None
    max_players: int | None
    min_playtime: int | None
    max_playtime: int | None
    min_age: int | None
    average_rating: float | None
    complexity: float | None
    users_rated: int | None
    categories: list[str]
    mechanics: list[str]


class BGGSearchResult(BaseModel):
    bgg_id: int
    title: str
    year_published: int | None
