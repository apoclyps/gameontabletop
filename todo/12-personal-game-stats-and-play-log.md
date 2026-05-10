# Personal Game Stats and Play Log

## Goal

Give each user a complete, personal view of their gaming life: every game played, how often, how well, and how much of their collection they've actually used — surfaced as a personal play log, a per-game history page, and a collection analytics dashboard.

## Background

Three existing todos establish the data foundation but leave a personal layer unbuilt:

- **Todo 07** (game result tracking) records competitive outcomes — wins, losses, placements, scores — in the context of organised sessions. It requires a full player list and outcome data; there is no way to simply log "I played Wingspan solo last Tuesday."
- **Todo 08** (collection) tracks what games a user owns. It has no concept of how often those games get played.
- **Todo 10** (BGG import) pulls historical play data into `game_results`. BGG plays frequently have no win/loss data, and the import discards non-competitive plays that don't fit the result schema.

This todo introduces `play_logs` — a lightweight personal play record that does not require competitive outcomes — and builds the statistics, per-game history, and collection analytics on top of the union of play logs and game results.

---

## Data Model

### `play_logs`

One row per person per game session. A play log is the minimal "I played this" record. It does not require outcomes, a full player list, or an organised event context.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| bgg_game_id | int nullable | FK → bgg_games; null for games not on BGG |
| game_title | varchar(300) | required; denormalised from BGG cache or entered manually |
| played_at | date | date of play; no time component (matches BGG play format) |
| player_count | smallint nullable | total number of players at the table |
| duration_minutes | smallint nullable | actual session length |
| location | varchar(200) nullable | free text: "Home", "The Dice Tower Café", etc. |
| notes | text nullable | personal notes about the session |
| personal_rating | smallint nullable | user's personal rating 1–10; separate from BGG community rating |
| game_result_id | UUID FK → game_results nullable | set when a full competitive result also exists for this play |
| source | enum(manual, bgg_import) | how this entry was created |
| bgg_play_id | int nullable | BGG play ID; used for deduplication on import |
| created_at | timestamptz | |
| UNIQUE | (user_id, bgg_play_id) WHERE bgg_play_id IS NOT NULL | prevents re-importing the same BGG play |

### Relationship to `game_results` (todo 07)

`play_logs` and `game_results` are complementary, not overlapping:

- A play log with `game_result_id = null` is a casual/solo/uncounted session
- A play log with `game_result_id` set is the same session as the linked result, seen from the perspective of one player
- When a `game_result` is created (todo 07), the system auto-creates a `play_log` for each player in `game_result_players` (source = `derived`) so that all plays appear in one place regardless of how they were recorded

**Total play count for a game** = `play_logs WHERE user_id = :me AND bgg_game_id = :id` — this covers manual logs, BGG imports, and plays derived from game results.

### Changes to todo 10 (BGG import)

Todo 10 currently writes BGG plays into `game_results`. This should be revised:

- BGG plays are written into `play_logs` (source = bgg_import) regardless of whether outcome data is present
- Where a BGG play has win/loss data for all players, also create a `game_result` and link it via `game_result_id`
- Where outcome data is absent or incomplete, the play log stands alone — it counts towards play totals without polluting result statistics
- The `bgg_play_id` UNIQUE constraint on `play_logs` handles deduplication (replacing the equivalent constraint on `game_results` described in todo 10)

---

## Statistics

All personal statistics are computed from `play_logs` (for play counts and personal context) and `game_result_players` (for win/loss). Stats are always scoped to the requesting user.

### Personal overview stats

| Stat | Source |
|---|---|
| Total distinct games played | `COUNT(DISTINCT bgg_game_id) FROM play_logs` |
| Total play sessions | `COUNT(*) FROM play_logs` |
| Total play time | `SUM(duration_minutes) FROM play_logs` |
| Games owned | `COUNT(*) FROM user_game_collections WHERE status = own` |
| Collection utilisation | distinct played / distinct owned (as %) |
| Shelf of shame | games in collection (status = own) with no matching play_log |
| Average plays per owned game | total plays on owned games / games owned |
| Plays this year | play_logs where `DATE_PART('year', played_at) = current_year` |
| Plays this month | play_logs in current calendar month |
| Most played game | bgg_game_id with highest play_log count |
| Most recently played | play_log with latest played_at |
| Longest session | play_log with highest duration_minutes |

### Per-game stats (for a specific `bgg_game_id`)

| Stat | Source |
|---|---|
| Total plays | play_logs count |
| First played | earliest played_at |
| Last played | latest played_at |
| Average duration | AVG(duration_minutes) vs BGG estimate |
| Personal rating | latest personal_rating on a play_log (or dedicated rating entry) |
| Win rate | game_result_players where is_winner / total result plays |
| Average score | AVG(score) from game_result_players |
| Best score | MAX(score) from game_result_players |
| Most played with | top co-players from game_result_players |
| Play frequency trend | plays per month over the last 12 months |
| In my collection? | user_game_collections status for this game |

### Collection analytics

| Stat | Description |
|---|---|
| Shelf of shame | Owned games with zero play logs — full list, sortable by date added |
| Played but not owned | Games with play logs where collection status is null or wishlist |
| Wishlist already played | Games on wishlist that have at least one play log (suggest moving to "own" or removing) |
| Play frequency by complexity | Bucketed by BGG weight: how many plays in light / medium / heavy bracket |
| Collection age | Average time since acquired_at for owned games; oldest unplayed |

---

## API Routes

### Play logs

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/me/plays` | required | All my play logs, paginated |
| POST | `/api/users/me/plays` | required | Log a casual play |
| PATCH | `/api/users/me/plays/{play_id}` | required | Edit notes, rating, duration |
| DELETE | `/api/users/me/plays/{play_id}` | required | Remove a play log (source = manual only) |
| GET | `/api/users/{id}/plays` | contextual | Another user's play logs (respects `stats_public`) |

`POST /api/users/me/plays` request body:

```json
{
  "bgg_game_id": 266192,
  "game_title": "Wingspan",
  "played_at": "2026-05-10",
  "player_count": 3,
  "duration_minutes": 75,
  "location": "Home",
  "notes": "Finally beat the bird feeder strategy.",
  "personal_rating": 9
}
```

`game_title` is required when `bgg_game_id` is null. When `bgg_game_id` is provided and the game is in the `bgg_games` cache, `game_title` is auto-populated if omitted.

Query parameters for `GET /api/users/me/plays`:

| Param | Type | Description |
|---|---|---|
| `bgg_game_id` | int | Filter to a specific game |
| `from` | date | Earliest played_at |
| `to` | date | Latest played_at |
| `source` | string | `manual`, `bgg_import` |
| `page` / `per_page` | int | Pagination |

### Statistics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/me/stats/overview` | required | Personal overview stats |
| GET | `/api/users/me/stats/collection` | required | Collection analytics |
| GET | `/api/users/me/stats/games/{bgg_game_id}` | required | Per-game stats for the authenticated user |
| GET | `/api/users/{id}/stats/overview` | contextual | Another user's overview (respects `stats_public`) |
| GET | `/api/users/{id}/stats/games/{bgg_game_id}` | contextual | Another user's per-game stats |
| GET | `/api/bgg/games/{bgg_game_id}` | required | Game detail page — metadata + community stats (cached from BGG) |

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration creates `play_logs` with all indexes and constraints; migration is reversible
- [ ] `POST /api/users/me/plays` returns `400` if `bgg_game_id` is null and `game_title` is also absent
- [ ] `DELETE` is blocked for plays with `source = bgg_import` or `source = derived`; return `403` with a message explaining the play came from an import or a recorded result
- [ ] When a `game_result` is created (todo 07 route), the system auto-creates `play_log` rows for each player in `game_result_players` with `source = derived` and `game_result_id` set; this is idempotent (second creation of the same result does not duplicate play logs)
- [ ] `GET /api/users/me/stats/overview` returns all overview stats in a single response; no N+1 queries — use a single SQL pass with window functions and conditional aggregates
- [ ] `GET /api/users/me/stats/collection` shelf-of-shame list is ordered by `acquired_at DESC` (most recently added unplayed games first)
- [ ] `personal_rating` is constrained to 1–10 at the database level (`CHECK (personal_rating BETWEEN 1 AND 10)`)
- [ ] All stat endpoints respect the `stats_public` flag from todo 07; private users return `404` for other requesters
- [ ] `GET /api/users/{id}/stats/games/{bgg_game_id}` returns `404` rather than a zero-count response when the user has no plays for that game, to avoid leaking the existence of plays when stats are private

### Frontend

- [ ] **Personal stats page** (`/stats`):
  - Summary cards: total games played, total plays, total play time, collection utilisation %
  - "Shelf of shame" section: grid of owned games with no plays, with a "Log a play" shortcut on each card
  - Play activity heatmap: a GitHub-style contribution graph showing plays per day over the last 12 months (one square per day, colour intensity by play count)
  - Top 5 most played games with play count and last played date
  - Recent plays list: last 10 play logs with game title, date, and duration
  - "Log a play" primary CTA button
- [ ] **Log a play form** (modal, accessible from the stats page, collection page, and per-game page):
  - BGG game search with free-text fallback
  - Date picker defaulting to today
  - Player count, duration, location, notes fields (all optional)
  - Personal rating selector (star or number picker, 1–10, optional)
  - Submit creates a `play_log`; if the user also wants to record a full competitive result they are offered a "Add full result" link after saving
- [ ] **Per-game page** (`/games/{bgg_game_id}`):
  - Game header: BGG artwork, title, player count range, complexity, BGG community rating
  - My stats panel: total plays, win rate, average score, personal rating, first/last played
  - Play history timeline: all play logs for this game, expandable — shows notes, duration, linked result if any
  - Play frequency chart: plays per month over the last 12 months as a bar chart
  - "Log a play" button pre-filled with this game
  - Collection status badge: "In my collection", "On my wishlist", "Not in collection" — with a quick-add button
  - If the user has no plays: show BGG metadata only with a prominent "Log your first play" CTA
- [ ] **Collection page enhancement** (extends todo 08):
  - Each game card gains a play count badge (e.g. "12 plays") drawn from `play_logs`
  - Shelf of shame filter: a toggle to show only owned games with zero plays
  - Sort by: play count (ascending shows least-played first), last played date
- [ ] **Profile page enhancement** (extends todo 08 summary row):
  - Update summary from "Owns 42 games · 3 on wishlist" to "Owns 42 games · 163 plays · 12% shelf of shame"

### Tests

- [ ] `tests/test_play_logs.py`:
  - Manual log create, edit, delete
  - Delete blocked for bgg_import and derived sources
  - `personal_rating` outside 1–10 range rejected at API level
  - Play log auto-created when a game_result is recorded (derived source)
  - Auto-creation is idempotent — duplicate not created on re-save
  - Pagination and date range filtering on `GET /api/users/me/plays`
- [ ] `tests/test_personal_stats.py`:
  - Overview stats return correct totals given a known set of play logs and results
  - Collection utilisation computed correctly (played distinct / owned distinct)
  - Shelf of shame excludes games with at least one play log
  - Per-game stats: win rate derived from game_result_players, play count from play_logs
  - `stats_public = false` returns `404` for other users on all stat endpoints
  - `GET /api/users/{id}/stats/games/{bgg_id}` returns `404` when user has no plays for that game

---

## Implementation Notes

- Place all stat query logic in `backend/app/services/stats.py` (established in todo 07) alongside the existing group and player stat functions; personal overview and collection analytics are new functions in the same module
- The play activity heatmap on the frontend is a pure client-side render from the paginated play log list — do not add a dedicated heatmap endpoint; fetch the last 365 days of play logs and compute the grid in the Vue component
- For the per-game page, the BGG metadata (artwork, description, player count, complexity) comes from `GET /api/bgg/games/{bgg_game_id}` which serves from the `bgg_games` cache (established in Phase 3 of the main plan); this page can therefore be linked to from anywhere a `bgg_game_id` is known without additional backend work
- `personal_rating` on `play_logs` represents the user's rating for that specific session; if a user plays the same game 10 times and rates it differently each time, the per-game stat shows the most recent rating. A future todo could introduce a separate `game_ratings` table for a single stable personal rating per game
- The `derived` source on auto-created play logs must not be exposed in the "source" filter on `GET /api/users/me/plays` — derived plays are an implementation detail; surface them simply as regular plays without origin labels in the UI
- Coordinate with todo 10: the BGG import job should write to `play_logs` (source = bgg_import) as its primary output, creating `game_results` only for plays that have complete win/loss data. Update the `bgg_import_jobs` counters to report `play_logs` created, not `game_results` created
