# Game Collection and Lending

## Goal

Let players catalogue the board games they own, mark which ones they are willing to lend, and see what games their friends have available — so that when planning a game night, anyone can quickly answer "who has Wingspan we could borrow?"

## Background

The plan already has a thin BGG collection cache (`user_bgg_collections`: user_id, bgg_game_id, synced_at) used to power the "N attendees own this game" badge on game suggestions. That table is a sync cache, not an ownership model. This feature replaces it as the canonical source of truth for a user's library and adds three things that don't exist yet:

1. **A richer collection model** — status, lendability, condition, notes, manual additions for games not on BGG
2. **A social graph** — friends/connections between users so collections can be shared
3. **A lending tracker** — records of who has borrowed what and whether it has been returned

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
| is_lendable | bool default false | owner is willing to lend this copy |
| condition | enum(new, like_new, good, fair, poor) nullable | physical condition of their copy |
| notes | text nullable | e.g. "missing 2 red cubes", "includes all expansions" |
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

### `game_loans`

Records an active or past loan of a game from one user to another.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| collection_entry_id | UUID FK → user_game_collections | which copy is being loaned |
| lender_user_id | UUID FK → users | denormalised from collection_entry |
| borrower_user_id | UUID FK → users | |
| status | enum(requested, active, returned, cancelled) | |
| requested_at | timestamptz | |
| loaned_at | timestamptz nullable | when lender confirmed and handed over |
| due_back_at | date nullable | agreed return date |
| returned_at | timestamptz nullable | when marked returned |
| lender_notes | text nullable | |
| borrower_notes | text nullable | |
| CHECK | lender_user_id != borrower_user_id | |

---

## API Routes

### Collections

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/me/collection` | required | My full collection |
| POST | `/api/users/me/collection` | required | Add a game manually |
| PATCH | `/api/users/me/collection/{entry_id}` | required | Update status, lendable flag, notes, etc. |
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
| GET | `/api/friends/collection` | required | Aggregate lendable games across all friends |
| GET | `/api/friends/collection?bgg_game_id={id}` | required | Which friends own a specific game |

### Lending

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/loans` | required | Request to borrow a game (borrower initiates) |
| GET | `/api/loans` | required | My loans — as lender and borrower combined |
| PATCH | `/api/loans/{loan_id}` | lender | Confirm loan (`active`) or decline (`cancelled`) |
| POST | `/api/loans/{loan_id}/return` | lender | Mark a loan returned |
| DELETE | `/api/loans/{loan_id}` | borrower | Cancel own request before lender confirms |

### Occurrence integration (extends existing route)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/occurrences/{id}/available-games` | group member | Lendable games from attendees who RSVPd yes/maybe |

Query parameters for `GET /api/friends/collection`:

| Param | Type | Description |
|---|---|---|
| `status` | string | Filter: `own`, `wishlist`, `want_to_play` (default: `own`) |
| `is_lendable` | bool | Filter to lendable games only (default: true) |
| `min_players` | int | Games that fit this player count |
| `max_players` | int | Games that fit this player count |
| `q` | string | Free-text search on game title |

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration creates `user_game_collections`, `user_friendships`, and `game_loans` tables; the existing `user_bgg_collections` sync cache table is retained for raw BGG data but `user_game_collections` becomes the primary read surface — the BGG sync job upserts into `user_game_collections` (source = bgg_sync) in addition to its existing cache write
- [ ] `collection_visible_to` is enforced on `GET /api/users/{user_id}/collection`: `public` returns all `own` entries; `friends` requires an accepted friendship; `private` returns `404` for everyone except the owner
- [ ] `GET /api/friends/collection` returns games deduplicated by `bgg_game_id`, with an `owners` array listing which friends have it and their `is_lendable` status — clients never need to make N requests
- [ ] A game can only be added to `game_loans` if the collection entry has `is_lendable = true` and no other loan for that entry is currently `active` — concurrent borrow requests against the same copy are blocked with `409 Conflict`
- [ ] When a loan is confirmed (`active`), the collection entry's `is_lendable` effective status in API responses reflects that the copy is currently out; a separate `on_loan` boolean is computed on read, not stored
- [ ] Friendship requests to an email address that matches no registered user send an invitation email with a sign-up link; the pending request is associated once the account is created
- [ ] Blocked users cannot send friend requests, see each other's collections, or appear in each other's friend search results
- [ ] `GET /api/occurrences/{id}/available-games` returns only games with `is_lendable = true` and no active loan, owned by attendees with an accepted RSVP, grouped by game with `lenders` listing each owning attendee

### Frontend

- [ ] **Collection page** (`/collection`):
  - Grid of game cards (BGG artwork, title, player count, status badge)
  - Tabs: Owned / Wishlist / Want to Play / Previously Owned
  - Per-card controls: toggle lendable, edit condition/notes, remove
  - "Add game" button opens a BGG search modal; selecting a game creates an `own` entry; free-text fallback for non-BGG games
  - "Sync from BGG" button triggers the sync and shows an updated-count toast on completion
  - Sort: alphabetical, recently added, player count
- [ ] **Friends list page** (`/friends`):
  - List of accepted friends with avatar, username, game count, lendable game count
  - Pending requests section (incoming and outgoing) with Accept / Decline actions
  - "Add friend" search by username or email
  - Clicking a friend navigates to their public collection view
- [ ] **Friend's collection view** (`/users/{username}/collection`):
  - Same grid layout as own collection, read-only
  - Shows only games visible to the viewer based on `collection_visible_to`
  - "Request to borrow" button on lendable games (disabled with tooltip if game is on loan)
  - Games currently on loan show "Currently lent out" badge
- [ ] **Friends' games page** (`/friends/collection`):
  - Aggregate view of all lendable games across all friends
  - Filter bar: player count, game title search
  - Each game card shows avatars of which friends own it
  - "Request to borrow" initiates a loan request
- [ ] **Loans page** (`/loans`):
  - Two tabs: "Borrowing" (loans where I am borrower) and "Lending" (loans where I am lender)
  - Lender view: pending requests to confirm/decline, active loans with a "Mark returned" button, past loans
  - Borrower view: pending requests, active loans with optional due date, past loans
  - Overdue loans (past `due_back_at` and still active) shown with a warning indicator
- [ ] **Occurrence page integration**: existing game suggestions list gains a "Who can bring this?" inline section showing attendee avatars for those who own and are willing to lend it, replacing the simpler "N attendees own this" badge
- [ ] **Profile page**: add a summary row ("Owns 42 games · 8 lendable · 3 on wishlist") with a link to the full collection
- [ ] **Collection visibility setting** on the profile settings page: global default (`public` / `friends` / `private`) that pre-fills `collection_visible_to` for new entries; individual overrides still available per game

### Notifications (email)

- [ ] **Friend request received** — "username wants to connect on Game On Tabletop"
- [ ] **Friend request accepted** — "username accepted your friend request"
- [ ] **Borrow request received** — lender notified when someone requests their game
- [ ] **Borrow confirmed** — borrower notified when lender confirms the loan
- [ ] **Borrow declined** — borrower notified when lender declines
- [ ] **Return reminder** — borrower emailed 2 days before `due_back_at` if set
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
- [ ] `tests/test_loans.py`:
  - Full loan lifecycle: request → confirm → return
  - Concurrent borrow conflict returns `409`
  - Cannot borrow from non-lendable entry
  - `on_loan` computed flag reflects active loan in collection response

---

## Implementation Notes

- Keep the existing `user_bgg_collections` table for the raw BGG sync cache; the BGG sync job should write to both tables — `user_bgg_collections` for the raw cache and `user_game_collections` (source = bgg_sync, status = own) for the canonical ownership view. This avoids a breaking change to the BGG sync code while making the richer table the API's read surface
- The `on_loan` field on collection responses is computed via a `LEFT JOIN game_loans ON ... AND status = 'active'` — do not add a stored boolean that can drift out of sync
- For the friendship query pattern, add a database view `v_friends` that returns `(user_id, friend_id)` pairs for all accepted friendships in both directions; query the view rather than writing the OR condition in every route
- Index `user_game_collections(user_id, status)` and `user_game_collections(bgg_game_id)` for the friends' aggregate collection query
- Index `user_friendships(addressee_id, status)` in addition to the primary `(requester_id, addressee_id)` unique index for incoming-request lookups
- The "request to borrow" flow is intentionally lightweight — it creates a loan record and sends an email; there is no in-app messaging system at this stage. A future todo can add in-app notifications or a messaging thread attached to a loan
- Loan requests to friends only: enforce at the API level that `lender_user_id` and `borrower_user_id` share an accepted friendship before a loan can be created; this prevents cold-contact borrow requests
