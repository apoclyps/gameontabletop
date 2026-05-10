# Game Collection and Bring Along

## Goal

Let players catalogue the board games they own and see what games friends have, so that when a game is selected for a session everyone knows whose copy is being used and who is responsible for bringing it.

## Background

The plan already has a thin BGG collection cache (`user_bgg_collections`: user_id, bgg_game_id, synced_at) used to power the "N attendees own this game" badge on game suggestions. That table is a sync cache, not an ownership model. This feature replaces it as the canonical source of truth for a user's library and adds:

1. **A richer collection model** — status (own / wishlist / want to play), manual additions for games not on BGG
2. **A social graph** — friends/connections so collections can be shared
3. **Bring-along assignment** — for each game selected at a session, one attendee is designated as bringing their copy; defaults to the event creator/host and can be reassigned

The plan's open question 3 ("extend BGG collection to want_to_play list") is resolved here.

---

## Data Model

### `user_game_collections`

Replaces `user_bgg_collections` as the canonical ownership record. BGG sync writes into this table; manual adds also write here.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| bgg_game_id | int nullable | FK → bgg_games; null for manually added games not on BGG |
| game_title | varchar(300) | required; denormalised from BGG cache or entered manually |
| game_thumbnail_url | varchar nullable | from BGG cache |
| min_players | smallint nullable | from BGG cache |
| max_players | smallint nullable | from BGG cache |
| complexity | numeric(3,2) nullable | BGG weight 1.0–5.0 |
| status | enum(own, wishlist, want_to_play, previously_owned) | |
| notes | text nullable | e.g. "includes all expansions", "missing 2 red cubes" |
| source | enum(bgg_sync, manual) | how this entry was added |
| acquired_at | date nullable | when they got the game |
| collection_visible_to | enum(public, friends, private) default friends | privacy per-game |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| UNIQUE | (user_id, bgg_game_id) WHERE bgg_game_id IS NOT NULL | one entry per BGG game per user |

### `user_friendships`

Bidirectional friendship graph with a pending-request flow.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| requester_id | UUID FK → users | user who sent the request |
| addressee_id | UUID FK → users | user who received it |
| status | enum(pending, accepted, declined, blocked) | |
| requested_at | timestamptz | |
| responded_at | timestamptz nullable | |
| UNIQUE | (requester_id, addressee_id) | one relationship record per pair |
| CHECK | requester_id != addressee_id | cannot friend yourself |

Accepted friendships are bidirectional: a single row covers both directions. Query as `WHERE (requester_id = :me OR addressee_id = :me) AND status = 'accepted'`.

### Changes to `game_suggestions` (extends the plan's Phase 3 table)

Add one column to the existing `game_suggestions` table:

| Column | Type | Notes |
|---|---|---|
| brought_by_user_id | UUID FK → users nullable | attendee responsible for bringing this copy; defaults to the occurrence's host/organiser on selection |

### Changes to `open_game_suggestions` (extends todo 06)

Same addition:

| Column | Type | Notes |
|---|---|---|
| brought_by_user_id | UUID FK → users nullable | defaults to the open game's host on creation |

---

## Bring-Along Logic

When a game's status is changed to `selected` on a `game_suggestion`:

1. Set `brought_by_user_id` to the occurrence's host user (the `night_occurrences` creator or the assigned host from the occurrence record)
2. If the host does not have that game in their `user_game_collections`, set `brought_by_user_id` to the user who suggested the game instead (they are more likely to own it)
3. If neither owns it, leave `brought_by_user_id` null — the organiser must assign it manually

The organiser can reassign `brought_by_user_id` to any attendee who has the game in their collection with `status = own`. The API validates the new assignee is both (a) attending with an RSVP of yes/maybe and (b) has the game in their collection.

For open games, `brought_by_user_id` on `open_game_suggestions` defaults to the event's `host_user_id` on creation and follows the same reassignment rules.

---

## API Routes

### Collections

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/me/collection` | required | My full collection |
| POST | `/api/users/me/collection` | required | Add a game manually |
| PATCH | `/api/users/me/collection/{entry_id}` | required | Update status, notes, visibility |
| DELETE | `/api/users/me/collection/{entry_id}` | required | Remove from collection |
| POST | `/api/users/me/bgg-sync` | required | Trigger BGG sync (existing route, now writes to this table) |
| GET | `/api/users/{user_id}/collection` | contextual | View another user's collection (respects visibility) |

### Friends

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/friends` | required | List accepted friends |
| POST | `/api/friends/request` | required | Send a friend request by username or email |
| GET | `/api/friends/requests` | required | Pending incoming requests |
| PATCH | `/api/friends/{friendship_id}` | required | Accept or decline a request |
| DELETE | `/api/friends/{friendship_id}` | required | Unfriend or cancel a sent request |
| POST | `/api/friends/{friendship_id}/block` | required | Block a user |
| GET | `/api/friends/collection` | required | Aggregate owned games across all friends |
| GET | `/api/friends/collection?bgg_game_id={id}` | required | Which friends own a specific game |

### Bring-along assignment

| Method | Path | Auth | Description |
|---|---|---|---|
| PATCH | `/api/games/{suggestion_id}/bring` | organiser | Assign or reassign who is bringing the game |
| GET | `/api/occurrences/{id}/available-games` | group member | Games in attendees' collections, grouped by game with owners listed |

`PATCH /api/games/{suggestion_id}/bring` request body:

```json
{ "brought_by_user_id": "<uuid>" }
```

Returns `400` if the assignee is not attending or does not own the game. Returns `400` if the suggestion is not in `selected` status.

Query parameters for `GET /api/friends/collection`:

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `own`, `wishlist`, `want_to_play` (default: `own`) |
| `min_players` | int | Games that fit this player count |
| `max_players` | int | Games that fit this player count |
| `q` | string | Free-text search on game title |

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration creates `user_game_collections` and `user_friendships`; adds `brought_by_user_id` to `game_suggestions` and `open_game_suggestions`; migration is reversible
- [ ] The existing `user_bgg_collections` sync cache is retained; the BGG sync job upserts into `user_game_collections` (source = bgg_sync, status = own) in addition to its existing cache write
- [ ] `collection_visible_to` is enforced on `GET /api/users/{user_id}/collection`: `public` returns all `own` entries; `friends` requires an accepted friendship; `private` returns `404` for everyone except the owner
- [ ] `GET /api/friends/collection` returns games deduplicated by `bgg_game_id` with an `owners` array listing which friends have it — clients never need to make N requests
- [ ] When a `game_suggestion` is set to `selected`, `brought_by_user_id` is automatically set per the default logic (host → suggester → null) in a service function, not inline in the route handler
- [ ] `PATCH /api/games/{suggestion_id}/bring` validates that the assignee is attending and owns the game; returns `400` with a descriptive message on either failure
- [ ] `GET /api/occurrences/{id}/available-games` returns attendees' `own` collection entries, grouped by `bgg_game_id`, with each game showing which attendees have it — used by the organiser to decide who should bring it
- [ ] Blocked users cannot send friend requests, see each other's collections, or appear in friend search results
- [ ] Friendship requests to an email address matching no registered user send an invitation email with a sign-up link; the pending request is associated once the account is created

### Frontend

- [ ] **Collection page** (`/collection`):
  - Grid of game cards (BGG artwork, title, player count, status badge)
  - Tabs: Owned / Wishlist / Want to Play / Previously Owned
  - Per-card controls: edit notes, change status, remove
  - "Add game" button opens a BGG search modal; free-text fallback for non-BGG games
  - "Sync from BGG" button triggers sync and shows an updated-count toast on completion
  - Sort: alphabetical, recently added, player count
- [ ] **Friends list page** (`/friends`):
  - List of accepted friends with avatar, username, game count
  - Pending requests section (incoming and outgoing) with Accept / Decline actions
  - "Add friend" search by username or email; group co-members shown as "People you play with" suggestions
  - Clicking a friend navigates to their collection view
- [ ] **Friend's collection view** (`/users/{username}/collection`):
  - Same grid layout as own collection, read-only
  - Shows only games visible to the viewer based on `collection_visible_to`
- [ ] **Friends' games page** (`/friends/collection`):
  - Aggregate view of all owned games across friends
  - Filter bar: player count, game title search
  - Each game card shows avatars of which friends own it
- [ ] **Occurrence and open game page — bring-along UI**:
  - Selected games show a "Brought by" row with the assigned attendee's avatar and username
  - Organiser/host sees an "Edit" control that opens a dropdown of attendees who own the game, populated from `GET /api/occurrences/{id}/available-games`
  - If `brought_by_user_id` is null (no owner found among attendees), the field shows "Not assigned — no attendee has this game" with an amber warning
  - Non-organisers see the assignment read-only
- [ ] **Profile page**: add a summary row ("Owns 42 games · 3 on wishlist") linking to `/collection`
- [ ] **Collection visibility setting** in profile settings: global default (`public` / `friends` / `private`) that pre-fills `collection_visible_to` for new entries; individual overrides still available per game

### Notifications (email)

- [ ] **Friend request received** — "username wants to connect on Game On Tabletop"
- [ ] **Friend request accepted** — "username accepted your friend request"
- [ ] **Bring-along assigned** — when an organiser assigns a different attendee to bring a game, that attendee is notified: "You've been asked to bring Wingspan to Saturday's session"
- [ ] **Invite to join** — non-registered email gets a sign-up invite when someone tries to add them as a friend

### Tests

- [ ] `tests/test_collection.py`:
  - Add, update, remove collection entries manually and via BGG sync upsert
  - `collection_visible_to` enforcement across all three levels
  - Duplicate BGG game rejected by UNIQUE constraint
- [ ] `tests/test_friends.py`:
  - Request, accept, decline, block flows
  - Blocked user cannot view collection or send requests
  - Friendship query covers both directions (requester and addressee)
  - Group co-member suggestions appear on the friends page
- [ ] `tests/test_bring_along.py`:
  - Selecting a game sets `brought_by_user_id` to host by default
  - Falls back to suggester if host does not own the game
  - Falls back to null if neither owns it
  - Organiser can reassign to any attending owner
  - Reassignment rejected if assignee is not attending
  - Reassignment rejected if assignee does not own the game
  - Non-organiser cannot reassign

---

## Implementation Notes

- Keep the existing `user_bgg_collections` table for the raw BGG sync cache; the BGG sync job writes to both tables — `user_bgg_collections` for the raw cache and `user_game_collections` (source = bgg_sync) for the canonical view
- Encapsulate the default bring-along assignment logic in `backend/app/services/collection.py` so it is independently testable and reusable across group occurrences and open games
- Add a database view `v_friends` returning `(user_id, friend_id)` pairs for all accepted friendships in both directions; use it in all friendship queries to avoid repeating the OR condition
- Index `user_game_collections(user_id, status)` and `user_game_collections(bgg_game_id)` for the friends' aggregate collection query
- Index `user_friendships(addressee_id, status)` for incoming-request lookups
- The "People you play with" friend suggestions query: `SELECT DISTINCT user_id FROM group_members WHERE group_id IN (my groups) AND user_id NOT IN (my friends) AND user_id != me` — run at page load with a low limit (e.g. 5 suggestions)
