# Board Game Night Scheduler — Design Plan

A Calendly-style scheduling platform for organising board game nights. Multi-tenant: any user can create groups, invite people, and run their own recurring events independently.

---

## Core User Problems

1. **When?** — Finding a date/time that works for enough people
2. **Where?** — Deciding on a location
3. **What?** — Choosing games given who is coming and what people own/want to play
4. **Who?** — Knowing who is actually coming that week
5. **Change management** — Handling postponements, cancellations, hold periods, and roster changes

---

## Key Design Decisions (answered upfront)

| Decision | Choice |
|---|---|
| Tenancy | Multi-tenant — groups are the top-level isolation unit |
| Polling model | Doodle-style poll to find first date → locks into recurring occurrence series |
| Guest access | Magic-link guests can RSVP/vote; registered users get history, preferences, notifications |
| Game selection | BoardGameGeek API integration — search, game details, attendees' collections |

---

## Data Model

### Entity Overview

```
User
 └─ GroupMember ──► Group ──► Location
                       └─ GroupInvite
                       └─ NightSeries ──► AvailabilityPoll ──► PollOption
                                                                    └─ PollResponse
                              └─ NightOccurrence ──► RSVP
                                                  └─ GameSuggestion ──► GameVote
GuestToken ──────────────────────────────────────────────────────────────────────►
BggGame (cache)
```

---

### Tables

#### `groups`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | varchar(100) | |
| description | text nullable | |
| slug | varchar(100) unique | URL-safe identifier |
| owner_id | UUID FK → users | |
| is_public | bool | public groups are discoverable |
| created_at | timestamptz | |

#### `group_members`
| Column | Type | Notes |
|---|---|---|
| group_id | UUID FK | composite PK |
| user_id | UUID FK | composite PK |
| role | enum(organiser, member) | |
| joined_at | timestamptz | |
| invited_by | UUID FK → users nullable | |

#### `group_invites`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| group_id | UUID FK | |
| email | varchar nullable | null = open link |
| token | varchar unique | random, URL-safe |
| role | enum(organiser, member) | default member |
| expires_at | timestamptz | |
| used_at | timestamptz nullable | |
| created_by | UUID FK → users | |

#### `locations`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| group_id | UUID FK | |
| name | varchar(200) | |
| address | text nullable | |
| is_virtual | bool | |
| virtual_url | varchar nullable | e.g. TTS / BGA link |
| notes | text nullable | parking, access codes, etc. |



#### `night_series`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| group_id | UUID FK | |
| title | varchar(200) | e.g. "Saturday Night Games" |
| description | text nullable | |
| status | enum(active, on_hold, cancelled, completed) | |
| recurrence | enum(once, weekly, biweekly, monthly, custom) | |
| rrule | varchar nullable | iCal RRULE string for custom |
| default_day_of_week | smallint nullable | 0=Mon … 6=Sun |
| default_start_time | time nullable | |
| default_duration_minutes | int nullable | |
| default_location_id | UUID FK nullable | |
| series_start_date | date nullable | first occurrence date |
| series_end_date | date nullable | null = indefinite |
| created_by | UUID FK → users | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

#### `night_occurrences`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| series_id | UUID FK | |
| title | varchar nullable | overrides series title |
| occurrence_date | date | |
| start_time | time | |
| end_time | time nullable | |
| location_id | UUID FK nullable | |
| status | enum(scheduled, postponed, cancelled) | |
| rsvp_deadline | timestamptz nullable | |
| game_vote_deadline | timestamptz nullable | |
| notes | text nullable | |
| postponed_from_date | date nullable | original date if postponed |
| is_auto_generated | bool | generated from rrule vs hand-created |
| created_at | timestamptz | |
| updated_at | timestamptz | |

#### `availability_polls`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| series_id | UUID FK | |
| title | varchar(200) | |
| description | text nullable | |
| deadline | timestamptz nullable | |
| status | enum(open, closed, resolved) | |
| chosen_option_id | UUID FK nullable | set when resolved |
| created_by | UUID FK → users | |
| created_at | timestamptz | |

#### `poll_options`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| poll_id | UUID FK | |
| proposed_date | date | |
| start_time | time | |
| end_time | time nullable | |
| location_id | UUID FK nullable | |
| display_order | smallint | |

#### `poll_responses`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| poll_id | UUID FK | |
| option_id | UUID FK | |
| user_id | UUID FK nullable | null for guests |
| guest_token_id | UUID FK nullable | |
| guest_name | varchar nullable | |
| response | enum(yes, no, maybe) | |
| responded_at | timestamptz | |
| UNIQUE | (option_id, user_id) | one response per person per option |
| UNIQUE | (option_id, guest_token_id) | |

#### `rsvps`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| occurrence_id | UUID FK | |
| user_id | UUID FK nullable | |
| guest_token_id | UUID FK nullable | |
| guest_name | varchar nullable | |
| response | enum(yes, no, maybe) | |
| note | text nullable | |
| responded_at | timestamptz | |
| UNIQUE | (occurrence_id, user_id) | |
| UNIQUE | (occurrence_id, guest_token_id) | |

#### `game_suggestions`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| occurrence_id | UUID FK | |
| suggested_by_user_id | UUID FK nullable | |
| bgg_game_id | int | BGG object ID |
| title | varchar(300) | denormalised from cache |
| thumbnail_url | varchar nullable | |
| min_players | smallint | |
| max_players | smallint | |
| complexity | numeric(3,2) nullable | BGG weight 1.0–5.0 |
| status | enum(suggested, shortlisted, selected, rejected) | |
| created_at | timestamptz | |
| UNIQUE | (occurrence_id, bgg_game_id) | no duplicates per night |

#### `game_votes`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| suggestion_id | UUID FK | |
| user_id | UUID FK | |
| vote | enum(up, down) | |
| UNIQUE | (suggestion_id, user_id) | one vote per person per game |

#### `guest_tokens`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| token | varchar unique | random, URL-safe |
| email | varchar nullable | |
| guest_name | varchar nullable | |
| group_id | UUID FK nullable | |
| series_id | UUID FK nullable | |
| occurrence_id | UUID FK nullable | |
| poll_id | UUID FK nullable | |
| expires_at | timestamptz | |
| created_at | timestamptz | |

#### `bgg_games` (cache)
| Column | Type | Notes |
|---|---|---|
| bgg_id | int PK | |
| title | varchar(300) | |
| year_published | smallint nullable | |
| min_players | smallint | |
| max_players | smallint | |
| complexity | numeric(3,2) nullable | weight |
| thumbnail_url | varchar nullable | |
| image_url | varchar nullable | |
| description | text nullable | |
| cached_at | timestamptz | re-fetch after 7 days |

#### `user_bgg_collections` (cache)
| Column | Type | Notes |
|---|---|---|
| user_id | UUID FK | composite PK |
| bgg_game_id | int | composite PK |
| synced_at | timestamptz | |

> User BGG username stored as `bgg_username varchar nullable` added to `users` table.

---

## Series Lifecycle State Machine

```
         [created]
             │
             ▼
     ┌── active ──────────────────────────────────────────────────────┐
     │   │ occurrence auto-generated from rrule                       │
     │   │ or manually created (once-off)                             │
     │   │                                                            │
     │   ▼                                                            │
     │  occurrence: scheduled ──► postponed (new date set)            │
     │                         └► cancelled                           │
     │                                                                │
     ├──► on_hold    (future occurrences paused; existing stay)       │
     │       └──► active (resumed)                                    │
     │                                                                │
     └──► cancelled  (terminal)                                       │
          completed  (end_date passed, terminal)                      │
                                                                      └┘
```

### Availability Poll → Occurrence flow

```
1. Organiser creates NightSeries (status = active, recurrence = weekly/etc.)
2. Before committing to a date, organiser creates AvailabilityPoll on the series
3. Poll options are proposed date/time slots
4. Members + guests respond (yes/no/maybe) via link
5. Organiser resolves poll → picks winning option → sets series_start_date
6. First NightOccurrence is created from the winning option
7. Subsequent occurrences auto-generated by rrule going forward
```

---

## API Routes

### Groups — `/api/groups`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/groups` | required | Create group |
| GET | `/api/groups` | required | List my groups |
| GET | `/api/groups/{group_id}` | member | Group detail |
| PATCH | `/api/groups/{group_id}` | organiser | Update group |
| DELETE | `/api/groups/{group_id}` | organiser | Delete group |
| GET | `/api/groups/{group_id}/members` | member | List members |
| DELETE | `/api/groups/{group_id}/members/{user_id}` | organiser | Remove member |
| POST | `/api/groups/{group_id}/invites` | organiser | Create invite link |
| GET | `/api/invites/{token}` | public | Resolve invite (preview) |
| POST | `/api/invites/{token}/accept` | required | Accept invite as user |

### Locations — `/api/groups/{group_id}/locations`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/groups/{group_id}/locations` | member | List locations |
| POST | `/api/groups/{group_id}/locations` | organiser | Add location |
| PATCH | `/api/locations/{location_id}` | organiser | Update location |
| DELETE | `/api/locations/{location_id}` | organiser | Remove location |

### Series — `/api/series`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/groups/{group_id}/series` | organiser | Create series |
| GET | `/api/groups/{group_id}/series` | member | List series |
| GET | `/api/series/{series_id}` | member | Series detail + occurrences |
| PATCH | `/api/series/{series_id}` | organiser | Update / put on hold / cancel |

### Occurrences — `/api/occurrences`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/series/{series_id}/occurrences` | member | List occurrences |
| POST | `/api/series/{series_id}/occurrences` | organiser | Create manual occurrence |
| GET | `/api/occurrences/{occurrence_id}` | member or guest | Occurrence detail |
| PATCH | `/api/occurrences/{occurrence_id}` | organiser | Postpone / cancel / update |
| POST | `/api/occurrences/{occurrence_id}/rsvp` | user or guest | RSVP |
| GET | `/api/occurrences/{occurrence_id}/rsvps` | member | List RSVPs |

### Polls — `/api/polls`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/series/{series_id}/polls` | organiser | Create poll |
| GET | `/api/polls/{poll_id}` | public (with token or member) | Poll detail + responses |
| POST | `/api/polls/{poll_id}/options` | organiser | Add option |
| DELETE | `/api/polls/{poll_id}/options/{option_id}` | organiser | Remove option |
| POST | `/api/polls/{poll_id}/respond` | user or guest | Submit response |
| POST | `/api/polls/{poll_id}/resolve` | organiser | Close poll and pick winner |

### Games — `/api/games`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/bgg/search` | required | Search BGG (`?q=`) |
| GET | `/api/bgg/game/{bgg_id}` | required | Game detail (cached) |
| POST | `/api/occurrences/{occurrence_id}/games` | member | Suggest game |
| GET | `/api/occurrences/{occurrence_id}/games` | member or guest | List suggestions + votes |
| POST | `/api/games/{suggestion_id}/vote` | member | Vote up/down |
| PATCH | `/api/games/{suggestion_id}` | organiser | Select / shortlist / reject |
| DELETE | `/api/games/{suggestion_id}` | organiser or suggester | Remove suggestion |

### BGG Collection Sync — `/api/users`

| Method | Path | Auth | Description |
|---|---|---|---|
| PATCH | `/api/users/me` | required | Set `bgg_username` |
| POST | `/api/users/me/bgg-sync` | required | Trigger BGG collection sync |

### Guest Access — `/api/guest`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/guest/{token}` | public | Resolve token → context object |
| POST | `/api/guest/{token}/rsvp` | public | RSVP as guest |
| POST | `/api/guest/{token}/poll` | public | Respond to poll as guest |

---

## BGG API Integration

BoardGameGeek exposes a free XML API 2 (`https://boardgamegeek.com/xmlapi2/`).

### Endpoints used

| BGG endpoint | Purpose |
|---|---|
| `/search?query={q}&type=boardgame` | Game search |
| `/thing?id={ids}&stats=1` | Game details + complexity weight |
| `/collection?username={u}&own=1&excludesubtype=boardgameexpansion` | User's owned games |

### Quirks to handle

- Collection requests return `HTTP 202` while BGG queues the job; must retry until `200`.
- Responses are XML; parse with `lxml` or `xml.etree.ElementTree`.
- Rate limit: no documented limit but keep ≤ 2 req/s to avoid 429s.
- Cache game records in `bgg_games` table; re-fetch if `cached_at` > 7 days old.
- Collection sync runs on-demand (user triggers) or lazily when viewing suggestions — not on every request.

### "In N attendees' collections" badge

When listing game suggestions for an occurrence, query `user_bgg_collections` for attendees who RSVP'd `yes` or `maybe`. Cross-reference with `bgg_game_id` to show how many people who are coming own the game.

---

## Recurrence Generation

Use `python-dateutil` `rrule` on the backend.

```python
from dateutil.rrule import rrule, WEEKLY, MO, SA
from datetime import date

# Example: every other Saturday starting 2026-06-07, up to 8 occurrences ahead
rule = rrule(WEEKLY, interval=2, byweekday=SA, dtstart=series_start, count=8)
```

### Generation strategy (serverless-friendly)

- On `GET /api/series/{id}`: generate occurrences up to `today + 8 weeks` if fewer than N are scheduled.
- On occurrence fetch: check if the next window needs expansion.
- Store generated dates in `night_occurrences` (`is_auto_generated = true`).
- This avoids needing a persistent background worker.
- Future: Vercel Cron (`vercel.json` cron) can call a `POST /api/internal/generate-occurrences` to proactively generate + send reminders.

### Series pause (on_hold)

- `status = on_hold` stops generation of future occurrences.
- Already-generated future occurrences remain (organiser can cancel individually).
- Resuming (`status = active`) resumes generation from today onward.

---

## Frontend Pages

```
/                          Dashboard — upcoming nights across all groups
/groups/new                Create group
/groups/{id}               Group overview — members, locations, series list
/groups/{id}/invite        Manage invite links
/groups/{id}/series/new    Create series (recurrence picker, location, poll option)
/series/{id}               Series detail — upcoming occurrences, polls, status
/series/{id}/poll/new      Create availability poll with date options
/poll/{id}                 Poll page — respond, live tally (registered + guest)
/occurrence/{id}           Occurrence — RSVP, game suggestions, voting, attendee list
/occurrence/{id}/games     Suggest + vote on games (BGG search embedded)
/join/{token}              Accept group invite (prompt sign-in or continue as guest)
/rsvp/{token}              Guest RSVP for specific occurrence
/poll-respond/{token}      Guest poll response page
/profile                   User profile — add BGG username, sync collection
/settings/bgg              BGG collection management
```

### Frontend tech additions

| Package | Purpose |
|---|---|
| `rrule` (npm) | Display recurrence descriptions ("Every other Saturday") |
| `date-fns` | Date formatting and arithmetic |
| `fast-xml-parser` | Parse BGG XML responses in the browser (or proxy through backend) |

---

## Notification Emails (SendGrid)

| Trigger | Recipient | Subject |
|---|---|---|
| Group invite created | invitee email | "You're invited to {Group}" |
| Poll created | all group members | "Help pick a date for {Series}" |
| Poll resolved | all respondents | "{Series} is happening on {date}" |
| Occurrence scheduled (auto) | all members | "Next {Series}: {date}" |
| RSVP reminder | non-responders | "Are you coming to {Series} on {date}?" |
| Occurrence postponed | all RSVPs | "{Series} has moved to {new date}" |
| Occurrence cancelled | all RSVPs | "{Series} on {date} is cancelled" |
| Game voting open | yes/maybe RSVPs | "Vote on games for {Series}" |
| Series put on hold | all members | "{Series} is on hold" |

---

## Implementation Phases

### Phase 1 — Group & Series Foundation

**Goal**: Groups, members, locations, recurring series, per-occurrence RSVP for registered users.

- [ ] DB migration: `groups`, `group_members`, `group_invites`, `locations`, `night_series`, `night_occurrences`, `rsvps`
- [ ] API: groups CRUD, members management, location CRUD
- [ ] API: series CRUD + recurrence generation with `python-dateutil`
- [ ] API: occurrence list/detail, manual occurrence creation, postpone/cancel
- [ ] API: RSVP (registered users only)
- [ ] Email: group invite, occurrence scheduled, RSVP reminder
- [ ] Frontend: dashboard, group page, series page, occurrence page, RSVP UI
- [ ] Frontend: recurrence picker component (once/weekly/biweekly/monthly)
- [ ] Frontend: invite management page
- [ ] Tests: group/series/occurrence/rsvp API tests

### Phase 2 — Availability Polling + Guest Access

**Goal**: Doodle-style polling to find the first date; magic-link guest participation.

- [ ] DB migration: `availability_polls`, `poll_options`, `poll_responses`, `guest_tokens`
- [ ] API: poll CRUD, poll respond, poll resolve → create first occurrence
- [ ] API: guest token generation + resolution endpoints
- [ ] API: guest RSVP, guest poll response
- [ ] Email: poll created, poll resolved
- [ ] Frontend: poll creation page (date/time option builder)
- [ ] Frontend: poll response page (works for guests)
- [ ] Frontend: `/join/{token}`, `/rsvp/{token}`, `/poll-respond/{token}` guest pages
- [ ] Tests: poll flow tests, guest token tests

### Phase 3 — BGG Integration + Game Voting

**Goal**: Search BGG, suggest games per occurrence, vote, show attendee collection overlap.

- [ ] DB migration: `game_suggestions`, `game_votes`, `bgg_games`, `user_bgg_collections`; add `bgg_username` to `users`
- [ ] Backend: BGG XML API client (async httpx), search + game detail + collection sync
- [ ] API: BGG search/game endpoints with DB cache
- [ ] API: game suggestion, vote, status management
- [ ] API: BGG collection sync trigger + collection in profile
- [ ] Email: game voting open notification
- [ ] Frontend: BGG search component (debounced, shows player count + complexity)
- [ ] Frontend: game suggestion list with vote UI and "N attendees own this" badge
- [ ] Frontend: BGG username + sync in profile page
- [ ] Tests: BGG client tests (mocked HTTP), game suggestion/vote tests

### Phase 4 — Polish & Vercel Cron

**Goal**: Proactive reminders and occurrence auto-generation without user-triggered requests.

- [ ] Vercel Cron: `POST /api/internal/generate-occurrences` — run nightly, generates 8-week window for all active series
- [ ] Vercel Cron: `POST /api/internal/send-reminders` — RSVP reminders 48h before occurrence, game-vote reminders 24h before deadline
- [ ] Series on-hold UI and resume flow
- [ ] Public group discovery page (if `is_public = true`)
- [ ] iCal export: `GET /api/occurrences/{id}/calendar.ics`
- [ ] BGG collection auto-sync (nightly, for users with `bgg_username` set)

---

## Security Considerations

- **Guest tokens**: short-lived (7 days default), scoped to a specific group/series/occurrence/poll. Tokens are random 32-byte URL-safe strings.
- **Group membership checks**: all series/occurrence/poll routes enforce that the requesting user is a member of the parent group.
- **Organiser-only actions**: series create/edit, poll resolve, game status changes, member removal.
- **BGG proxy**: route BGG requests through the backend to avoid CORS issues and apply rate limiting. Never expose BGG API key (it doesn't require one, but the proxy lets you cache and throttle).
- **RSVP enumeration**: RSVP lists visible to group members only (not guests); guest tokens give access to their own occurrence/poll only.

---

## Open Questions / Future Decisions

1. **Time zones**: Store all times in UTC, derive display TZ from group's preferred timezone (add `timezone` field to `groups`). Not in Phase 1.
2. **Push notifications**: SendGrid covers email. Browser push or SMS (Twilio) deferred.
3. **Game library (owned vs. wishlist)**: BGG collection currently filtered to owned games only. Extend to `want_to_play` list in a later phase.
4. **Waitlist**: If max attendees is set, late RSVPs could go on a waitlist. Not scoped.
5. **Voting cutoff**: Automatically close game voting at `game_vote_deadline`. Needs a Cron job (Phase 4).
6. **Custom recurrence**: RRULE string stored in `night_series.rrule` but UI for custom rules (e.g. "first Saturday of the month") deferred until Phase 4.
