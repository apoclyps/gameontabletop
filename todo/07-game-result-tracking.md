# Game Result Tracking

## Goal

Let players record the outcome of every game played — who won, who lost, and what the scores were — then surface those results at three levels: the specific night it was played, the group it belongs to, and each individual player's personal statistics.

## Background

The plan already models which games are played at a night (`game_suggestions` with `status = selected`) and who attended (`rsvps`). What is missing is the actual outcome of each game once the night is over. Result tracking completes the loop: plan → play → record → reflect.

There are three contexts in which a game can be played and recorded:

1. **Group occurrence** — a game played at a `night_occurrence`, typically linked to a `game_suggestion`
2. **Open game** — a game played at an `open_game` event (see todo `06-open-games.md`)
3. **Standalone** — a casual game recorded directly by a player outside any organised event (for completeness of personal stats)

Results must accommodate four play modes:
- **Competitive** — one winner, ranked placements, everyone else loses
- **Scored** — all players have a numeric score; ranking derived from scores
- **Cooperative** — the whole group wins or loses together (e.g. Pandemic, Spirit Island)
- **Team** — players grouped into named teams; the winning team's players win

---

## Data Model

### `game_results`

One row per game played (a single play-through, not per player).

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| recorded_by_user_id | UUID FK → users | who entered the result |
| occurrence_id | UUID FK → night_occurrences nullable | group night context |
| game_suggestion_id | UUID FK → game_suggestions nullable | the specific selected game on that night |
| open_game_id | UUID FK → open_games nullable | open event context |
| group_id | UUID FK → groups nullable | denormalised from occurrence for stats queries |
| bgg_game_id | int nullable | FK → bgg_games cache |
| game_title | varchar(300) | denormalised; required when bgg_game_id is null |
| game_thumbnail_url | varchar nullable | denormalised from BGG cache |
| play_mode | enum(competitive, scored, cooperative, team) | |
| cooperative_outcome | enum(win, loss) nullable | set when play_mode = cooperative |
| duration_minutes | smallint nullable | how long the game took |
| notes | text nullable | free text ("close game!", "played Orléans expansion") |
| played_at | timestamptz | when the game was played |
| created_at | timestamptz | |
| CHECK | at most one of occurrence_id, open_game_id is non-null | standalone if both null |

### `game_result_players`

One row per participant per game result.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| game_result_id | UUID FK | |
| user_id | UUID FK nullable | null for guest participants |
| guest_name | varchar nullable | required when user_id is null |
| team | varchar(100) nullable | team label for team play_mode (e.g. "Red", "Resistance") |
| placement | smallint nullable | 1 = first place; null for cooperative |
| score | numeric(10, 2) nullable | raw score for scored/competitive games |
| outcome | enum(win, loss, draw, cooperative_win, cooperative_loss) | |
| is_winner | bool | true for placement=1 or cooperative_win or winning team |
| UNIQUE | (game_result_id, user_id) | one row per registered player per result |

---

## Derived Statistics

Statistics are computed from `game_results` and `game_result_players` — no separate summary table is needed until query performance requires it. All stats respect the context they are requested in (night / group / player).

### Night-level stats (`/api/occurrences/{id}/results`, `/api/open-games/{id}/results`)

- List of all games played that night, in order played
- For each game: title, thumbnail, duration, play mode
- For each game: player list with placement, score, and outcome
- Total games played and total play time for the session
- Player of the night: the user with the most wins across all games played

### Group-level stats (`/api/groups/{id}/stats`)

| Stat | Description |
|---|---|
| Total games played | Count of `game_results` linked to the group |
| Total play sessions | Count of distinct `occurrence_id` values with results |
| Most played game | `bgg_game_id` with highest result count |
| Top player (win rate) | Member with highest win percentage (min 5 games) |
| Leaderboard | Per-member: games played, wins, win rate — sortable |
| Per-game breakdown | For each game played in the group: play count, avg duration, who has won it most |
| Head-to-head matrix | Win/loss record between each pair of members |

### Player-level stats (`/api/users/{id}/stats`, `/api/users/me/stats`)

| Stat | Description |
|---|---|
| Games played | Total result rows for this player |
| Wins | Rows where `is_winner = true` |
| Win rate | Wins / games played (shown as %) |
| Win streak | Current consecutive wins (chronological) |
| Best win streak | Longest historical streak |
| Favourite game | Game they have played most often |
| Best game | Highest win rate with ≥ 3 plays |
| Worst game | Lowest win rate with ≥ 3 plays |
| Nemesis | Player who beats them most often in shared games |
| Biggest rival | Player they have played against most |
| Cooperative record | Cooperative win/loss separately tracked |
| Play time | Total `duration_minutes` accumulated |
| Recent results | Last 10 games with outcome and date |

Stats can be scoped to a specific group with a `?group_id=` query param.

---

## API Routes

### Game Results

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/occurrences/{id}/results` | organiser or attendee | Record a game result for a night |
| GET | `/api/occurrences/{id}/results` | group member | All results for a night |
| POST | `/api/open-games/{id}/results` | host or joined player | Record a result for an open game |
| GET | `/api/open-games/{id}/results` | public | All results for an open game |
| POST | `/api/results` | required | Record a standalone game result |
| GET | `/api/results/{result_id}` | contextual | Result detail with all players |
| PATCH | `/api/results/{result_id}` | recorder only | Correct a result (within 48 hours) |
| DELETE | `/api/results/{result_id}` | recorder or organiser | Remove a result |

### Statistics

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/occurrences/{id}/stats` | group member | Night summary stats |
| GET | `/api/open-games/{id}/stats` | public | Open game night summary stats |
| GET | `/api/groups/{id}/stats` | group member | Group leaderboard and aggregates |
| GET | `/api/users/{id}/stats` | public | Another player's public stats |
| GET | `/api/users/me/stats` | required | Authenticated user's full stats |

### Query parameters for stats endpoints

| Param | Type | Description |
|---|---|---|
| `bgg_game_id` | int | Filter stats to a specific game |
| `from` | date | Start of date range |
| `to` | date | End of date range |
| `group_id` | UUID | Scope player stats to a specific group |

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration creates `game_results` and `game_result_players` tables with all constraints and indexes
- [ ] Migration is reversible
- [ ] `play_mode` drives validation: `cooperative_outcome` required when `play_mode = cooperative`; `placement` required when `play_mode = competitive` or `scored`; `team` required when `play_mode = team`
- [ ] On create, the API validates that all submitted `user_id` values are members/attendees of the parent occurrence or open game
- [ ] `is_winner` is computed server-side from `placement`, `outcome`, and `team` — clients never send it directly
- [ ] For `scored` play mode, `placement` is derived server-side by ranking `score` values; the client sends scores only
- [ ] PATCH is blocked if the result is older than 48 hours (return `403` with a clear message); organisers and admins are exempt
- [ ] `GET /api/groups/{id}/stats` computes the leaderboard and per-game breakdown in a single query pass (avoid N+1 queries)
- [ ] `GET /api/users/{id}/stats` respects privacy: a user can make their stats private via a `stats_public` flag on their profile (add column to `users` table); private stats return `404` for other users
- [ ] All stat queries are covered by indexes on `(game_result_id, user_id)`, `(group_id, played_at)`, `(bgg_game_id)`, and `(user_id, is_winner)`

### Frontend

- [ ] **Occurrence page** — new "Results" tab alongside the existing RSVP and game suggestions tabs:
  - Timeline of games played that night, each expandable to show the full player leaderboard
  - "Record a game" button (visible to attendees who RSVPd yes/maybe)
- [ ] **Open game page** — same "Results" tab treatment as occurrence pages
- [ ] **Record result form** (modal or dedicated page `/results/new`):
  - Game picker: BGG search or free-text fallback
  - Play mode selector that reveals the appropriate fields (placement / score / team / cooperative outcome)
  - Player picker pre-populated with attendees; allows adding guests by name
  - Duration field (optional)
  - Notes field (optional)
  - Score entry table for scored games with real-time placement preview
  - Confirmation step showing the final standings before submission
- [ ] **Group stats page** (`/groups/{id}/stats`):
  - Summary cards: total games, total sessions, most played game, top player
  - Leaderboard table sortable by wins, win rate, games played
  - Per-game breakdown accordion: each game with a mini leaderboard of who has won it most within the group
  - Head-to-head matrix (collapsible, shown only for groups with ≥ 3 members)
  - Date range filter
- [ ] **Player profile** — stats panel below profile info:
  - Win rate ring chart or stat cards (games played, wins, win rate, play time)
  - Favourite game and best game shown with BGG artwork
  - Nemesis and biggest rival shown with avatar
  - Recent results list (game title, date, outcome badge)
  - Tab to switch between "all time" and per-group stats
- [ ] Stats are visible without login where the player's profile is public; a lock icon indicates private stats

### Tests

- [ ] `tests/test_results.py` covers:
  - Recording each play mode (competitive, scored, cooperative, team)
  - Server-side `is_winner` and `placement` derivation
  - 48-hour PATCH window enforcement
  - Attendee validation (cannot add a non-attendee to a result)
  - Permission checks (organiser exempt from 48h window)
- [ ] `tests/test_stats.py` covers:
  - Night summary stats for a session with multiple games
  - Group leaderboard correctness with known result fixtures
  - Player win rate, streak, nemesis derivation
  - `stats_public = false` returns `404` for other users
  - `group_id` scoping on player stats

---

## Implementation Notes

- Add `stats_public bool NOT NULL DEFAULT true` to the `users` table via a new Alembic migration
- Keep stat queries in a dedicated `backend/app/services/stats.py` module, not inline in route handlers — they are complex enough to warrant isolation and independent testing
- The head-to-head matrix is expensive for large groups; compute it only when explicitly requested and add a `?include_h2h=true` query param to opt in
- Use PostgreSQL window functions (`RANK() OVER (PARTITION BY game_result_id ORDER BY score DESC)`) for server-side placement derivation — avoid doing this in Python
- Win streak calculation: use a `ROW_NUMBER() - ROW_NUMBER() FILTER (WHERE is_winner)` gaps-and-islands approach in SQL
- For the frontend score-entry table, sort rows in real time by descending score and preview the derived placement so the recorder can spot mistakes before submitting
- This feature can launch without BGG integration — `game_title` text is sufficient for recording; add the BGG artwork and metadata later once the cache tables are in place
