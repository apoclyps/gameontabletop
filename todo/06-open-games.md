# Open Games

## Goal

Allow any user to advertise a public game event — at a café, pub, community space, or online — that anyone can discover and join without needing a group membership. This is the equivalent of a public noticeboard: "I'm running Twilight Imperium at The Dice Tower on Saturday, looking for 3 more players."

## Background

The existing design (see `plan/board-game-night-scheduler.md`) centres on **groups**: closed communities where members are invited and series are private by default. Open Games are a separate, lighter-weight concept — no group required, publicly listed, and joinable by any visitor (registered or guest).

Two event shapes are needed:
- **Single game** — one specific game being played, a fixed player count (e.g. "need 4 players for Gloomhaven")
- **Game night** — open session at a venue where multiple games will be played; the host sets a rough capacity but games are decided on the night or via suggestions

This feature depends on the BGG integration (todo `01-openapi-specification.md` covers API structure; BGG cache tables are described in the plan's Phase 3). The `bgg_games` cache table should be in place before implementing game-specific open events, but game nights without a fixed game can ship earlier.

---

## Data Model

### `open_games`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| host_user_id | UUID FK → users | creator and primary organiser |
| title | varchar(200) | e.g. "Twilight Imperium at The Anchor" |
| description | text nullable | free text for additional detail |
| event_type | enum(single_game, game_night) | |
| status | enum(open, full, cancelled, completed) | `full` when player_count = max_players |
| venue_name | varchar(200) nullable | e.g. "The Dice Tower Café" |
| venue_address | text nullable | full address for in-person events |
| is_virtual | bool default false | |
| virtual_url | varchar nullable | e.g. BGA/TTS link, revealed to joined players only |
| starts_at | timestamptz | date + time of the event |
| ends_at | timestamptz nullable | optional end time |
| max_players | smallint nullable | null = unlimited |
| min_players | smallint nullable | minimum for the game to run |
| bgg_game_id | int nullable | FK → bgg_games; set for single_game events |
| game_title | varchar(300) nullable | denormalised from BGG cache |
| game_thumbnail_url | varchar nullable | denormalised from BGG cache |
| experience_level | enum(any, beginner, intermediate, experienced) nullable | |
| notes | text nullable | e.g. "bring your own snacks", "parking available" |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `open_game_players`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| open_game_id | UUID FK | |
| user_id | UUID FK nullable | null for guest sign-ups |
| guest_name | varchar nullable | required when user_id is null |
| guest_email | varchar nullable | optional; used to send confirmation |
| status | enum(joined, waitlisted, cancelled) | |
| joined_at | timestamptz | |
| UNIQUE | (open_game_id, user_id) | one row per registered user |

### `open_game_suggestions` (game night only)

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| open_game_id | UUID FK | |
| suggested_by_user_id | UUID FK nullable | |
| bgg_game_id | int nullable | |
| title | varchar(300) | |
| thumbnail_url | varchar nullable | |
| min_players | smallint nullable | |
| max_players | smallint nullable | |
| created_at | timestamptz | |
| UNIQUE | (open_game_id, bgg_game_id) | no duplicate suggestions |

---

## API Routes

All public-read routes require no authentication. Write routes require a verified user account.

### Open Games — `/api/open-games`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/open-games` | public | List upcoming open games (paginated, filterable) |
| POST | `/api/open-games` | required | Create an open game |
| GET | `/api/open-games/{id}` | public | Event detail; hides `virtual_url` unless joined |
| PATCH | `/api/open-games/{id}` | host only | Update title, description, time, capacity |
| DELETE | `/api/open-games/{id}` | host only | Cancel event (sets status = cancelled) |
| POST | `/api/open-games/{id}/join` | user or guest | Join or request a spot |
| DELETE | `/api/open-games/{id}/leave` | user | Leave event (or cancel waitlist spot) |
| GET | `/api/open-games/{id}/players` | public | Player list (name + avatar only; no emails) |
| POST | `/api/open-games/{id}/suggestions` | joined user | Suggest a game (game night events only) |
| GET | `/api/open-games/{id}/suggestions` | public | List game suggestions for a game night |
| DELETE | `/api/open-games/{id}/suggestions/{suggestion_id}` | host or suggester | Remove suggestion |

### Query parameters for `GET /api/open-games`

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter by status: `open`, `full` (default: `open`) |
| `event_type` | string | `single_game` or `game_night` |
| `from` | date | Earliest `starts_at` (default: today) |
| `to` | date | Latest `starts_at` |
| `is_virtual` | bool | Filter to online events |
| `page` | int | Pagination offset |
| `per_page` | int | Results per page (max 50) |

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration creates `open_games`, `open_game_players`, and `open_game_suggestions` tables
- [ ] Migration is reversible (downgrade drops all three tables)
- [ ] A `require_host` FastAPI dependency blocks PATCH/DELETE to non-hosts with `403`
- [ ] Joining a full event (player_count = max_players) automatically sets the new player's status to `waitlisted`
- [ ] When a player leaves or cancels, the first `waitlisted` player is automatically promoted to `joined` and (if they provided an email) sent a notification
- [ ] `virtual_url` is redacted from the `GET /api/open-games/{id}` response unless the requesting user has a `joined` row in `open_game_players`
- [ ] `status` transitions to `full` automatically when the joined count reaches `max_players`; transitions back to `open` when a player leaves and max_players is no longer reached
- [ ] `GET /api/open-games` returns only events with `starts_at` in the future and `status != cancelled` by default
- [ ] Host cannot leave their own event via the leave endpoint; they must cancel the event instead
- [ ] Past events (`starts_at < now()`) are automatically set to `completed` status (via the generate-occurrences Cron job from the main plan's Phase 4, or lazily on fetch)

### Frontend

- [ ] `/open-games` — public discovery page, no login required:
  - Card grid of upcoming events showing title, venue, date/time, game (if single_game), player count (`3 / 6 players`), and event type badge
  - Filter bar: event type toggle (all / game night / single game), virtual/in-person toggle, date range
  - "Host an open game" CTA button (redirects to login if unauthenticated)
  - Pagination or infinite scroll
- [ ] `/open-games/new` — create form (auth required):
  - Event type selector (single game / game night) that conditionally shows the BGG game search field
  - BGG game search component (reused from the plan's game suggestion UI)
  - Venue name + address fields with a "Virtual event" toggle that hides address and shows a URL field
  - Date/time picker, optional end time
  - Max players field with helper text ("leave blank for unlimited")
  - Min players field with helper text ("event may not run below this number")
  - Experience level selector
  - Notes / free text field
- [ ] `/open-games/{id}` — event detail page:
  - Full event info: title, host (avatar + username), venue/map link, date/time, game artwork (if BGG-linked), description, notes
  - Player count indicator and list of joined players (avatars + names)
  - "Join" / "Leave" / "Join waitlist" button based on current user's status and event capacity
  - Host-only: "Edit" and "Cancel event" controls
  - For game night events: game suggestion list with an "Add suggestion" button (visible to joined players)
  - `virtual_url` is shown to joined players only, with a lock icon and copy button
  - Status badge: `Open`, `Full — join waitlist`, `Cancelled`, `Completed`
- [ ] A featured open games widget on the main dashboard showing the next 3 upcoming open events
- [ ] `/open-games/{id}` is shareable: the URL works without login and shows public event info

### Notifications (email)

- [ ] **Join confirmation** — sent to the joining user (and guest email if provided) when status = `joined`
- [ ] **Waitlist confirmation** — sent when status = `waitlisted`
- [ ] **Off waitlist** — sent when a waitlisted player is promoted to `joined`
- [ ] **Event cancelled** — sent to all `joined` and `waitlisted` players when the host cancels
- [ ] **Event reminder** — sent to all `joined` players 24 hours before `starts_at`

### Tests

- [ ] `tests/test_open_games.py` covers:
  - Create, read, update, cancel flows
  - Join as registered user and as guest
  - Waitlist promotion when a player leaves
  - Capacity enforcement (join → waitlisted when full)
  - `virtual_url` redaction for non-joined users
  - Host-only enforcement on PATCH/DELETE
  - `GET /api/open-games` filtering and pagination

---

## Implementation Notes

- Implement as a standalone router `backend/app/api/open_games.py` mounted at `/api/open-games`; follow the same structure as `auth.py` and `users.py`
- The player list endpoint should never expose email addresses; return only `{ username, display_name, avatar_url }` for registered users and `{ guest_name }` for guests
- Guest join flow mirrors the guest RSVP token pattern from the main plan's Phase 2 — generate a short-lived token and email it to the guest so they can cancel their own spot later
- Status transitions (`open` ↔ `full`, `completed`) should be encapsulated in a service layer function rather than scattered across route handlers
- This feature can ship before the BGG integration — single-game events can accept a free-text game name initially and add `bgg_game_id` lookup later; use `game_title varchar` as the fallback
- Index `open_games(starts_at, status)` for efficient listing queries
- The discovery page must work without authentication; ensure no auth middleware is applied globally to the `/api/open-games` GET routes
