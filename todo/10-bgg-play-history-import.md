# BGG Play History Import

## Goal

Let users import their complete play history from BoardGameGeek into Game On Tabletop so that their existing win/loss records, game statistics, and play counts are reflected from day one rather than starting from zero.

## Background

BGG exposes play history through its XML API v2 (`/xmlapi2/plays`). Each play record includes the game, date, location, comments, and per-player data: BGG username, display name, score, win/loss flag, and whether it was a first play. This is the canonical export format for BGG Stats (the third-party app) — plays logged there sync back to BGG, making the BGG plays API the single integration point for all BGG-ecosystem data.

The game result schema (todo `07-game-result-tracking.md`) was designed for native recording. Two fields need adding to support imported plays:

- `source` enum(`native`, `bgg_import`) on `game_results` — distinguishes imported records from natively recorded ones
- `bgg_play_id` int on `game_results` — BGG's own play ID, used for deduplication on re-import

A user's `bgg_username` is already planned as a field on the `users` table (Phase 3 of the main plan). The import cannot proceed without it.

---

## BGG Plays API

Base URL: `https://boardgamegeek.com/xmlapi2/plays`

| Parameter | Description |
|---|---|
| `username` | BGG username (required) |
| `page` | Page number; 100 plays per page |
| `mindate` / `maxdate` | ISO date range filter — used for incremental sync |
| `type=thing` | Filter to board game plays only |

The response is XML. Each `<play>` element contains:

```xml
<play id="12345678" date="2024-03-15" quantity="1" length="0" incomplete="0" nowinstats="0" location="Home">
  <item name="Wingspan" objectid="266192" />
  <players>
    <player username="alice_bgg" name="Alice" startposition="1" color="" score="74" new="0" win="1" rating="0" />
    <player username="" name="Bob" startposition="2" color="" score="61" new="0" win="0" rating="0" />
  </players>
  <comments>Great game, Alice dominated the bird feeder.</comments>
</play>
```

Key fields:
- `play.id` — BGG's unique play ID; store in `bgg_play_id` for deduplication
- `play.date` — date played (YYYY-MM-DD); no time component
- `play.length` — duration in minutes (often 0 when not filled in by the user)
- `play.location` — free text location string
- `play.quantity` — number of plays recorded in one entry (usually 1, occasionally > 1 for casual logging)
- `item.objectid` — BGG game ID; maps to `bgg_game_id`
- `item.name` — game title; maps to `game_title`
- `player.username` — BGG username; used to match against `users.bgg_username`
- `player.name` — display name; used as `guest_name` when username doesn't match any user
- `player.win` — `1` if this player won, `0` otherwise
- `player.score` — numeric score string; empty string if not recorded

---

## Data Model Changes

### Changes to `game_results` (from todo 07)

Add two columns to the existing table definition:

| Column | Type | Notes |
|---|---|---|
| source | enum(native, bgg_import) default native | how this result was created |
| bgg_play_id | int nullable | BGG play ID; used for deduplication |
| UNIQUE | (recorded_by_user_id, bgg_play_id) WHERE bgg_play_id IS NOT NULL | prevents re-importing the same play |

### Changes to `game_result_players` (from todo 07)

| Column | Type | Notes |
|---|---|---|
| attribution_confirmed | bool default true | false for BGG-matched players who have not yet accepted the attribution |
| bgg_username | varchar(100) nullable | the BGG username from the play record, retained for post-import manual linking |

### New table: `bgg_import_jobs`

Tracks the state of an import so users can see progress and the process can survive serverless cold starts via polling.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| status | enum(pending, running, completed, failed, cancelled) | |
| mode | enum(full, incremental) | full reimports all plays; incremental fetches since last import |
| date_from | date nullable | earliest play date to import (null = all time) |
| date_to | date nullable | latest play date to import (null = today) |
| total_pages | int nullable | set once first page is fetched |
| pages_fetched | int default 0 | |
| plays_found | int default 0 | total plays discovered on BGG |
| plays_imported | int default 0 | new plays written to game_results |
| plays_skipped | int default 0 | plays already present (bgg_play_id matched) |
| plays_failed | int default 0 | plays that errored during import |
| error_message | text nullable | last error if status = failed |
| started_at | timestamptz | |
| completed_at | timestamptz nullable | |

---

## Import Logic

### Play mode detection

BGG plays do not carry a `play_mode` field. Infer it from the `bgg_games` cache:

1. If the game has the BGG mechanic **"Cooperative Game"** (mechanic ID 2023) → `play_mode = cooperative`; set `cooperative_outcome = win` if all players have `win = 1`, else `loss`
2. If all players in the play have non-empty `score` values → `play_mode = scored`; derive `placement` server-side by ranking scores descending
3. Otherwise → `play_mode = competitive`; set `placement = 1` for `win = 1` players, null for others (multiple winners are possible in BGG plays)

If the `bgg_games` cache entry is missing for a game, fetch it from the BGG API before deciding play mode. Store the mechanic list on `bgg_games` to avoid re-fetching.

### Player matching

For each player in a BGG play:

1. If `player.username` is non-empty, look up `users WHERE bgg_username = player.username`
   - Match found → create `game_result_players` with `user_id`, `attribution_confirmed = false` (the matched user has not been asked to confirm)
   - No match → create `game_result_players` with `guest_name = player.name`, `bgg_username = player.username`
2. If `player.username` is empty → create with `guest_name = player.name`

The importing user's own plays are matched automatically and set `attribution_confirmed = true` (they initiated the import and implicitly confirm their own records).

### `play.quantity > 1`

Occasionally BGG plays log multiple plays in one entry (e.g., `quantity="3"`). Expand these into the number of separate `game_results` rows equal to `quantity`, all sharing the same `bgg_play_id`, date, and players — but without individual outcome data (BGG does not store per-play data within a multi-play entry). Set `play_mode = competitive`, all outcomes null, and add a note: `"Imported from BGG: {quantity} plays logged together"`.

### Deduplication

Before writing each play, check for an existing `game_results` row with matching `(recorded_by_user_id, bgg_play_id)`. If found, skip (increment `plays_skipped`). This makes re-triggering the import safe at any time.

### Rate limiting

The BGG API has no published rate limit but is sensitive to rapid requests. Apply a 500ms delay between page fetches. If BGG returns `HTTP 429`, back off exponentially starting at 5 seconds. If BGG returns `HTTP 202` (queued response), retry after 2 seconds up to 5 times before failing that page.

---

## API Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/users/me/bgg-import` | required | Start a BGG play import job |
| GET | `/api/users/me/bgg-import` | required | Get status of the most recent import job |
| GET | `/api/users/me/bgg-import/{job_id}` | required | Get status of a specific import job |
| DELETE | `/api/users/me/bgg-import/{job_id}` | required | Cancel a running import |
| GET | `/api/users/me/bgg-import/history` | required | List all past import jobs |
| GET | `/api/users/me/results/unlinked` | required | Unmatched players from imports that can be linked |
| POST | `/api/users/me/results/unlinked/{player_id}/link` | required | Link a guest player row to an app user |
| POST | `/api/results/{result_id}/confirm-attribution` | required | Matched user confirms or rejects their attribution |

### `POST /api/users/me/bgg-import` request body

```json
{
  "mode": "full",
  "date_from": "2020-01-01",
  "date_to": null
}
```

- `mode = full` ignores existing `bgg_play_id` matches and re-evaluates all plays (useful after the player-matching logic improves); `mode = incremental` only fetches plays since the last successful import's most recent play date
- Returns the `bgg_import_job` object immediately; the import runs asynchronously via a Vercel Cron-triggered internal endpoint

---

## Acceptance Criteria

### Backend

- [ ] Alembic migration adds `source`, `bgg_play_id` columns to `game_results`; `attribution_confirmed`, `bgg_username` columns to `game_result_players`; creates `bgg_import_jobs` table
- [ ] Migration is reversible
- [ ] `POST /api/users/me/bgg-import` returns `400` if `bgg_username` is not set on the user's profile
- [ ] `POST /api/users/me/bgg-import` returns `409` if a job with `status = running` already exists for the user
- [ ] BGG XML is parsed with `lxml`; malformed XML responses are caught and logged without crashing the job; that page is marked failed and the job continues
- [ ] Play mode detection correctly classifies cooperative games using mechanic ID 2023 from the `bgg_games` cache
- [ ] `quantity > 1` plays are expanded into separate rows as described, all with null outcome data
- [ ] Re-running a full import does not create duplicate `game_result_players` rows for already-imported plays (bgg_play_id deduplication enforced by UNIQUE constraint)
- [ ] Mechanic list is added to the `bgg_games` cache schema and populated during the existing game detail fetch; the import uses this without additional BGG API calls if the cache is warm
- [ ] Attribution confirmation endpoint: `confirm` sets `attribution_confirmed = true`; `reject` removes the `user_id` and replaces it with `guest_name` from the stored `bgg_username`
- [ ] All BGG HTTP calls go through the existing BGG client module (established in Phase 3); rate limiting and retry logic lives there, not in the import job

### Frontend

- [ ] **Import page** (`/settings/bgg-import` or as a tab within `/settings/integrations`):
  - Prerequisite check: if `bgg_username` is not set, show a prompt to set it first with a link to `/profile`
  - "Import all plays" button with a date range override (optional)
  - "Incremental sync" button to fetch only new plays since the last import
  - Progress display while a job is running: pages fetched, plays imported, plays skipped — updates by polling `GET /api/users/me/bgg-import` every 5 seconds
  - Completion summary: "Imported 847 plays across 163 games. 23 plays already existed and were skipped."
  - Import history table: date, mode, plays imported, status
- [ ] **Attribution review panel** (shown after import completes if any unconfirmed attributions exist):
  - Lists every `game_result_players` row where `attribution_confirmed = false` — i.e., other users matched by BGG username
  - The matched user sees this panel in their own settings when they next log in: "Alice has imported plays that include you. Do you want to include these in your stats?"
  - Confirm → `attribution_confirmed = true`; stats update immediately
  - Reject → player row converted to guest entry; stats unaffected
- [ ] **Unlinked players panel** (accessible from import results):
  - Lists guest player rows from imported plays that had a BGG username but no matching app account
  - For each, shows the BGG username and a user search to manually link them to an existing app user
  - Linking sends the matched user an attribution confirmation notification
- [ ] Stats pages (profile, group) display imported results identically to native results; a small "BGG" badge on individual result cards distinguishes the source for context but does not affect aggregates

### Notifications

- [ ] Email sent to the importing user on job completion: summary of plays imported, link to attribution review if any unconfirmed attributions exist
- [ ] Email (and configured channels from todo 09) sent to each matched user: "username has shared {N} play records with you from BGG — confirm to include them in your stats"

### Tests

- [ ] `tests/test_bgg_import.py`:
  - Parses a fixture BGG XML response and produces correct `game_results` and `game_result_players` rows
  - Play mode detection for cooperative (mechanic 2023 present), scored (all players have scores), and competitive (fallback)
  - `quantity > 1` expansion produces the correct number of rows
  - Deduplication: re-running import on already-imported plays skips them all
  - Malformed XML on one page is logged and skipped; job continues with remaining pages
  - Rate limit (429) response triggers retry with backoff
  - Import blocked when `bgg_username` is unset
  - Import blocked when another job is already running

---

## Implementation Notes

- The import job must survive Vercel's 60-second serverless function timeout. Structure the job as a page-by-page loop driven by the Vercel Cron endpoint (`POST /api/internal/bgg-import-tick`): each cron invocation fetches one page of plays, writes results, updates `bgg_import_jobs.pages_fetched`, and exits. The cron fires every minute. When `pages_fetched = total_pages`, the job is marked complete. This avoids holding a long-lived HTTP connection
- Alternatively, if a background queue is available (e.g., Upstash QStash), dispatch one message per page for true parallel processing — but the page-by-page sequential approach is simpler and respects BGG's rate sensitivity
- BGG play date is date-only (no time). Store `played_at` as the BGG date at midnight UTC and add a note in the UI that time of play is not available for imported records
- `play.location` from BGG (e.g., "Home", "Board Game Café") has no equivalent field in `game_results`; append it to `notes` as "Location: {location}" during import so the information is not lost
- Do not auto-link a BGG username to an app user without the matched user's confirmation — importing someone else's plays into their profile without consent is a privacy violation. The `attribution_confirmed = false` + notification flow is the correct gate
- BGG play data for plays logged without win/loss information (e.g., plays where all `win` attributes are 0 and no one is marked as winning) should be imported with all outcomes set to `null` rather than inventing a loser; these show up in stats as "unscored plays" and are excluded from win rate calculations
- After a successful import, trigger a `bgg_games` cache refresh for any game IDs in the imported plays that are older than 7 days, so artwork and player counts are current for the stats UI
