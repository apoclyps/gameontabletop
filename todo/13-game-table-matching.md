# Game Table Matching

## Goal

Let players at an upcoming games night propose games they want to play and recruit opponents or co-players from the confirmed attendee list. Once enough players confirm their seats, the table locks in and is prominently displayed on the games night page so everyone can see who is playing what.

---

## Background

Currently the games night page (OccurrencePage) shows RSVPs — who is coming — but nothing about what games will actually be played at the table. This feature bridges that gap: players with a yes/maybe RSVP can propose game tables, challenge specific opponents to a 1v1, and see a live board of locked tables during the night.

This feature is independent of the game collection (todo 08); game titles are free text with an optional BGG ID. No ownership requirement.

---

## Table Types

### Open table
Player proposes a game with a seat range (min/max players). Any attendee (yes or maybe RSVP) can join. The table locks automatically when the confirmed seat count reaches `min_players`. The proposer can also manually lock once minimum is met.

Example: "Wingspan — 3–5 players, need at least 2 more."

### Direct challenge
Player challenges a specific attendee to a game. The challenged player must accept or decline. On acceptance the table immediately locks (both players confirmed).

Example: "Chess 1v1 against Sarah."

---

## Data Model

### `game_tables`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| occurrence_id | UUID FK → night_occurrences CASCADE | |
| proposed_by | UUID FK → users | |
| game_bgg_id | int nullable | optional BGG game reference |
| game_title | varchar(300) | required; free text |
| table_type | varchar(10) | `open` or `challenge` |
| min_players | smallint | ge 2; default 2 |
| max_players | smallint | ge min_players |
| status | varchar(10) | `open`, `locked`, `cancelled` |
| notes | text nullable | optional context ("looking for casual players") |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `game_table_seats`

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| table_id | UUID FK → game_tables CASCADE | |
| user_id | UUID FK → users | |
| status | varchar(10) | `confirmed` or `pending` (challenge target awaiting response) |
| seated_at | timestamptz | |
| UNIQUE | (table_id, user_id) | no duplicate seats |

**Seat lifecycle:**
- Proposer's seat is created as `confirmed` when the table is created
- Open table join: seat created as `confirmed` immediately (joining = confirming)
- Challenge target: seat created as `pending`; transitions to `confirmed` on accept, or is deleted on decline

**Lock trigger:** after any seat confirmation, if `confirmed_count >= min_players`, `game_tables.status` is set to `locked` automatically.

---

## Constraints and Rules

- A user can only propose or join a table if they have an RSVP (`yes` or `maybe`) for that occurrence
- A user can only appear once on any given table
- Can't join a `locked` or `cancelled` table
- Can't join your own challenge (proposer is already seated)
- `max_players` is enforced: join is rejected if `confirmed_count == max_players`
- A user can leave a table **only** if it is still `open` (not yet locked)
- Cancelling a table (proposer or organiser) deletes all seats and marks status `cancelled`
- Once locked, the table cannot be unlocked (no partial cancellations)

---

## API Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/occurrences/{id}/tables` | required | Propose a game table (open or challenge) |
| GET | `/api/occurrences/{id}/tables` | required | List all tables for this night |
| PATCH | `/api/tables/{table_id}` | required | Update title/notes (proposer, open state only) |
| DELETE | `/api/tables/{table_id}` | required | Cancel a table (proposer or organiser) |
| POST | `/api/tables/{table_id}/join` | required | Join an open table |
| POST | `/api/tables/{table_id}/leave` | required | Leave a table (open state only) |
| POST | `/api/tables/{table_id}/respond` | required | Accept or decline a challenge (target user only) |
| POST | `/api/tables/{table_id}/lock` | required | Manually lock (proposer, when confirmed ≥ min) |

### `POST /api/occurrences/{id}/tables` request body

**Open table:**
```json
{
  "table_type": "open",
  "game_title": "Wingspan",
  "game_bgg_id": 266192,
  "min_players": 3,
  "max_players": 5,
  "notes": "Casual play, beginners welcome"
}
```

**Challenge:**
```json
{
  "table_type": "challenge",
  "game_title": "Chess",
  "challenged_user_id": "uuid-of-target-player"
}
```
For challenges `min_players` and `max_players` are both fixed at 2.

### `POST /api/tables/{table_id}/respond` request body
```json
{ "accepted": true }
```

### Response model `GameTableOut`

```json
{
  "id": "uuid",
  "occurrence_id": "uuid",
  "proposed_by": "uuid",
  "proposed_by_username": "string",
  "game_title": "string",
  "game_bgg_id": null,
  "table_type": "open",
  "min_players": 3,
  "max_players": 5,
  "status": "open",
  "notes": null,
  "seats": [
    { "user_id": "uuid", "username": "string", "status": "confirmed" }
  ],
  "confirmed_count": 1,
  "created_at": "datetime"
}
```

---

## Frontend

### Occurrence page — game tables section

Add a "Game tables" section to `OccurrencePage.vue` between the RSVP section and the "Who's coming" list.

**Locked tables** appear first with a clear "Playing tonight" heading. Each locked table card shows:
- Game title (bold)
- Player avatars/names, all confirmed
- A lock icon or "Confirmed" badge

**Open tables** follow with a "Looking for players" heading. Each card shows:
- Game title, proposer name, seats remaining (e.g. "2 / 5 seats filled")
- "Join" button (hidden if at max, if user already seated, or if table is locked)
- For challenge targets: "Accept" and "Decline" buttons instead of Join

**Pending challenges** received by the current user surface as a dismissible alert at the top of the section: "[Username] challenged you to [game] — Accept / Decline."

**"Propose a game" button** — visible to anyone with yes/maybe RSVP; hidden if occurrence is cancelled. Opens the propose form (inline expand or modal).

### Propose a game form

Fields:
- **Table type** toggle: Open table / 1v1 Challenge
- **Game title** — free-text input with optional BGG autocomplete (reuses the BGG search from collection page if available, otherwise plain text)
- **Challenge opponent** — dropdown of attendees (yes/maybe RSVPs), only shown when type = challenge
- **Min players** / **Max players** — number inputs, only shown when type = open (min ≥ 2, max ≥ min)
- **Notes** — optional textarea

### Visibility during the night

The occurrence page is the "during the night" view. Locked tables should be clearly distinguished and sorted above open tables so the board is easy to read when the group is gathered around someone's laptop.

---

## Acceptance Criteria

### Backend

- [ ] `POST /api/occurrences/{id}/tables` returns `403` if the user has no RSVP or RSVP is `no`
- [ ] Proposer's seat is auto-created as `confirmed` on table creation
- [ ] For `challenge` type, challenged player's seat is created as `pending`; `min_players` and `max_players` are both set to 2 regardless of payload
- [ ] `POST /api/tables/{id}/join` returns `403` if user has no yes/maybe RSVP, `409` if already seated, `409` if table is locked or cancelled, `409` if at `max_players`
- [ ] `POST /api/tables/{id}/respond` with `accepted: false` deletes the pending seat; does not change table status
- [ ] `POST /api/tables/{id}/respond` with `accepted: true` sets seat to `confirmed` and immediately locks the table (challenge tables always have 2/2 on accept)
- [ ] Lock trigger fires after any join or accept: if `confirmed_count >= min_players`, set `status = locked`
- [ ] `POST /api/tables/{id}/lock` returns `400` if `confirmed_count < min_players`
- [ ] `POST /api/tables/{id}/leave` returns `409` if table is `locked`
- [ ] Cancelling a table (DELETE) marks it `cancelled` and deletes all associated seats; only proposer or group organiser may cancel
- [ ] `GET /api/occurrences/{id}/tables` returns all non-cancelled tables ordered by status (`locked` first) then `created_at`

### Frontend

- [ ] Game tables section appears on OccurrencePage for any user with a yes/maybe RSVP
- [ ] Locked tables appear above open tables with distinct styling
- [ ] Pending challenge alert shown at top of section when the current user has an unresolved pending seat
- [ ] "Propose a game" button hidden for users without a yes/maybe RSVP and for cancelled occurrences
- [ ] Challenge opponent dropdown lists only users with yes/maybe RSVP, excluding the proposer
- [ ] Join button disabled/hidden when: table full, user already seated, table locked or cancelled
- [ ] Joining updates seat counts immediately (optimistic update or re-fetch)
- [ ] Leaving a table removes the user's card from the seat list

### Tests (`tests/test_game_tables.py`)

- [ ] Propose open table — succeeds with yes RSVP, fails with no RSVP, fails with no RSVP at all
- [ ] Propose challenge — challenged user gets pending seat
- [ ] Join open table — auto-confirms, triggers lock at min_players
- [ ] Join full table — rejected with 409
- [ ] Join locked table — rejected with 409
- [ ] Challenge accept — table locks immediately
- [ ] Challenge decline — pending seat deleted, table stays open (should not happen for a 2-seat table — it's cancelled)
- [ ] Leave open table — succeeds
- [ ] Leave locked table — rejected with 409
- [ ] Cancel table — only proposer or organiser can cancel
- [ ] List tables — locked first, cancelled excluded

---

## Implementation Notes

- Place router in `backend/app/api/game_tables.py`; register on `api_router` in `main.py`
- The lock trigger is a helper `_maybe_lock(table, session)` called after any seat confirmation; it checks `confirmed_count >= min_players` and sets `status = locked`
- `GET /api/occurrences/{id}/tables` must return `confirmed_count` and `seats` in a single query to avoid N+1; use a joined load or subquery
- The BGG autocomplete on the propose form is optional at first — plain free-text is sufficient; BGG search can be wired in when the BGG integration (todo 10) is implemented
- Keep the occurrence page performant: fetch tables in the existing `onMounted` alongside RSVPs (parallel `Promise.all`)
