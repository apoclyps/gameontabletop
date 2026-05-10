# Scheduled Games for Game Nights

## Goal

Allow members to schedule one or more games for a game night (NightOccurrence). A night can have several games running simultaneously (e.g. two 1v1 games in parallel). Display the next upcoming occurrence — with its scheduled game list — prominently on the Group page.

## Background

The data model already has: **Group → NightSeries → NightOccurrence → RSVP**. There is no concept of which games will be played at a given occurrence. This todo adds `OccurrenceGame` rows (one per game slot), a set of CRUD endpoints to manage them, a lightweight `GET /groups/{id}/next-occurrence` endpoint, and the frontend wiring to show it on the Group page and the Occurrence page.

---

## Data Model

### New table: `occurrence_games`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| occurrence_id | UUID FK → night_occurrences (CASCADE) | |
| added_by_user_id | UUID FK → users (SET NULL) | member who added this slot |
| bgg_game_id | int nullable | BGG game ID for linked games |
| game_title | varchar(300) | required; free-text or from BGG cache |
| game_thumbnail_url | varchar nullable | from BGG cache or left blank |
| min_players | smallint nullable | |
| max_players | smallint nullable | |
| complexity | Numeric(3,2) nullable | BGG weight 1.0–5.0 |
| status | varchar(20) default 'proposed' | `proposed` · `confirmed` · `played` · `skipped` |
| notes | text nullable | e.g. "teaching game, 3 players max tonight" |
| display_order | smallint default 0 | controls render order |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Indexes:** `(occurrence_id, display_order)` for ordered listing.

No uniqueness constraint — the same game can be scheduled twice (e.g. two simultaneous 1v1 matches of the same title).

---

## Backend

### Alembic migration

`005_add_occurrence_games.py` (or next available version number — check `alembic/versions/`)

- Creates `occurrence_games` table with all columns above
- Adds index on `(occurrence_id, display_order)`
- Reversible: `drop_table("occurrence_games")`

### Model (`app/models/scheduler.py`)

Add `OccurrenceGame` class to the existing file alongside `NightOccurrence`.

### Schemas (`app/schemas/scheduler.py`)

```python
class OccurrenceGameCreate(BaseModel):
    game_title: str
    bgg_game_id: int | None = None
    game_thumbnail_url: str | None = None
    min_players: int | None = None
    max_players: int | None = None
    complexity: Decimal | None = None
    notes: str | None = None
    display_order: int = 0

class OccurrenceGameUpdate(BaseModel):
    game_title: str | None = None
    status: Literal["proposed", "confirmed", "played", "skipped"] | None = None
    notes: str | None = None
    display_order: int | None = None

class OccurrenceGameResponse(BaseModel):
    id: uuid.UUID
    occurrence_id: uuid.UUID
    added_by_user_id: uuid.UUID | None
    bgg_game_id: int | None
    game_title: str
    game_thumbnail_url: str | None
    min_players: int | None
    max_players: int | None
    complexity: Decimal | None
    status: str
    notes: str | None
    display_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

Also add `NextOccurrenceResponse` (see Group endpoint below).

### New endpoints (`app/api/occurrences.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/occurrences/{id}/games` | member | List all games for this occurrence, ordered by `display_order` |
| POST | `/occurrences/{id}/games` | member | Add a game slot |
| PATCH | `/occurrences/{id}/games/{game_id}` | organiser or adder | Update title, status, notes, order |
| DELETE | `/occurrences/{id}/games/{game_id}` | organiser or adder | Remove game slot |

**Business rules:**
- Any group member may add a game (`proposed` status).
- Organisers may change status to `confirmed`, `played`, or `skipped`.
- The member who added the game or any organiser may delete it.
- No cap on the number of games per occurrence (multiple simultaneous games allowed).

### New endpoint (`app/api/groups.py`)

```
GET /groups/{group_id}/next-occurrence
```

Returns the single next upcoming occurrence across all series in the group (earliest `occurrence_date + start_time` that is in the future and `status = 'scheduled'`), enriched with:
- All scheduled `OccurrenceGame` rows for that occurrence
- RSVP counts (`yes`, `no`, `maybe`)
- The series title

Response schema `NextOccurrenceResponse`:
```python
class NextOccurrenceResponse(BaseModel):
    occurrence_id: uuid.UUID
    series_id: uuid.UUID
    series_title: str
    occurrence_date: date
    start_time: time
    end_time: time | None
    title: str | None
    status: str
    rsvp_counts: dict[str, int]
    games: list[OccurrenceGameResponse]
```

Returns `404` if no upcoming occurrence exists (group page handles this gracefully).

### `app/main.py`

No new router needed — new routes are added to the existing `occurrences` and `groups` routers.

### Tests

**`tests/test_occurrence_games.py`** — new file:
- Add a game to an occurrence → 201, game returned
- List games → ordered by `display_order`
- Non-member cannot add → 403
- Update status to `confirmed` as organiser → 200
- Update status as regular member (not adder) → 403
- Adder can update their own game → 200
- Delete by organiser → 204
- Delete by adder → 204
- Delete by other member → 403

**`tests/test_groups.py`** (existing or new):
- `GET /groups/{id}/next-occurrence` → returns the earliest future occurrence with games
- Returns 404 when no future occurrences exist
- Games list is empty when none have been added

---

## Frontend

### Group page (`src/pages/GroupPage.vue`)

Add a **"Next event"** card at the top of the page body, above the Series section.

```
┌─────────────────────────────────────────────────────┐
│ Next event                          → View full night│
│ Wednesday 14 May · 7:00 pm                          │
│ from: Monthly Boardgame Night                       │
│                                                     │
│ Games planned:                                      │
│  🎲 Wingspan           confirmed   2–5 players      │
│  🎲 Azul               proposed    2–4 players      │
│                                                     │
│ RSVPs: 4 going · 1 maybe · 0 declined               │
└─────────────────────────────────────────────────────┘
```

- Fetches `GET /groups/{id}/next-occurrence` in parallel with existing group/series/members calls
- If `404` (no upcoming event), shows a soft prompt: *"No upcoming events — create a series to schedule one."*
- Game rows show thumbnail (or PuzzlePieceIcon fallback), title, player count, status badge
- "View full night" links to `/occurrences/{occurrence_id}`
- Skeleton loaders while loading

### Occurrence page (`src/pages/OccurrencePage.vue`)

Add a **"Games"** section below the RSVP section:
- Lists `OccurrenceGame` rows fetched from `GET /occurrences/{id}/games`
- Each row: thumbnail, title, player count, complexity (if set), status badge, notes (collapsed)
- **Add game** button (all members): opens an inline form with fields for game title (+ optional BGG ID), player counts, notes
- Status badge is a dropdown for organisers (proposed → confirmed → played / skipped)
- Remove button visible to organisers and the game's adder
- Skeleton loaders while loading; empty state: *"No games scheduled yet — add one below."*

---

## Acceptance Criteria

### Backend
- [ ] `occurrence_games` table created by migration; migration is reversible
- [ ] `GET /occurrences/{id}/games` returns games ordered by `display_order`
- [ ] `POST /occurrences/{id}/games` — any member can add; status defaults to `proposed`
- [ ] `PATCH /occurrences/{id}/games/{game_id}` — organiser or adder only
- [ ] `DELETE /occurrences/{id}/games/{game_id}` — organiser or adder only
- [ ] `GET /groups/{id}/next-occurrence` returns the earliest future `scheduled` occurrence with embedded games and RSVP counts
- [ ] `GET /groups/{id}/next-occurrence` returns 404 when no future occurrence exists
- [ ] Multiple games with the same `bgg_game_id` can coexist on one occurrence (no uniqueness block)
- [ ] All tests pass

### Frontend
- [ ] Group page shows "Next event" card with date, series title, RSVP counts, and game list
- [ ] Group page shows graceful empty state when no upcoming event
- [ ] Occurrence page shows games section with add/edit/remove controls
- [ ] Thumbnail image with PuzzlePieceIcon fallback for games without artwork
- [ ] Status badge renders correct colour: `proposed` (slate), `confirmed` (teal/primary), `played` (emerald), `skipped` (amber)
- [ ] Frontend build passes (`npm run build`)
- [ ] Existing unit tests pass

---

## Implementation Notes

- The "next occurrence" query joins `night_occurrences` → `night_series` filtering on `series.group_id = :group_id`, `occ.occurrence_date >= today`, `occ.status = 'scheduled'`, ordered `occurrence_date ASC, start_time ASC LIMIT 1`.
- `display_order` on `OccurrenceGame` allows organisers to pin a particular game to the top of the list (e.g. "main game of the night" first). Default 0 = append order.
- BGG lookup is out of scope here — the game title is free-text. A future todo can add a BGG search autocomplete; for now organisers type the name.
- The `OccurrencePage.vue` already exists and shows RSVPs; the games section is added below it — do not restructure the page, only append.
- Keep the Group page card compact: show at most 3 games inline with a "+ N more" link if there are more.
