# Public Pages and Avatar Upload

## Goal

Make the platform partially browsable without an account: upcoming games nights from public groups are discoverable on an explore page, and user profiles are viewable by anyone (unless the owner opts out). Separately, let authenticated users upload an avatar photo, stored in Supabase Storage and served over the CDN.

---

## Background

Several fields are already in place but unused:

- `users.avatar_url` — stored but never written; no upload endpoint exists
- `users.bio`, `users.display_name` — stored but not surfaced on the profile page UI
- `groups.is_public` — column exists (default `false`) but no UI control and no public query uses it

What is missing:

- `users.profile_public` and `users.stats_public` flags (migration required)
- Supabase Storage bucket + upload endpoint
- Public API routes (no auth) for profiles and upcoming events
- Frontend pages: `/explore`, `/users/:username`
- Profile page controls: public toggle, stats toggle, avatar upload

---

## Data Model Changes

### Migration: `006_add_profile_visibility`

```sql
ALTER TABLE users
  ADD COLUMN profile_public BOOLEAN NOT NULL DEFAULT TRUE,
  ADD COLUMN stats_public   BOOLEAN NOT NULL DEFAULT TRUE;
```

No other schema changes are required. `avatar_url`, `bio`, `display_name`, and `groups.is_public` already exist.

---

## Supabase Storage

### Bucket

| Setting | Value |
|---|---|
| Bucket name | `avatars` |
| Public | yes — objects are readable without a token |
| Max file size | 2 MB |
| Allowed MIME types | `image/jpeg`, `image/png`, `image/webp` |

### Object path

```
avatars/{user_id}
```

One file per user; uploading a new avatar overwrites the previous one. No extension in the path — the Content-Type header carries the format.

### CDN URL pattern

```
https://{SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/avatars/{user_id}
```

This URL is what gets stored in `users.avatar_url`. Supabase Image Transformations can be appended as query params (`?width=128&height=128`) to serve thumbnails without a separate resize step.

### Backend upload flow

The file travels through the FastAPI backend (not directly from browser to Supabase) so that the existing JWT auth can be enforced server-side:

1. Client sends `POST /api/users/me/avatar` as `multipart/form-data` with a single `file` field
2. Backend validates: content type must be `image/jpeg | image/png | image/webp`; size ≤ 2 MB
3. Backend calls the Supabase Storage REST API (`PUT /storage/v1/object/avatars/{user_id}`) with the service key
4. On success, backend writes the CDN URL to `users.avatar_url` and returns the updated `UserResponse`

### New environment variable

`SUPABASE_SERVICE_KEY` — the Supabase project's service-role key (already available in the Supabase dashboard → Settings → API). Must be added to the Vercel backend environment.

### New Python dependency

`python-multipart` — required by FastAPI to parse `multipart/form-data` file uploads.

---

## API Routes

### Public routes (no `Authorization` header required)

| Method | Path | Description |
|---|---|---|
| GET | `/api/public/events` | Upcoming occurrences from public groups |
| GET | `/api/public/events/{occurrence_id}` | Single public occurrence detail |
| GET | `/api/public/profile/{username}` | Public profile for a user |

**`GET /api/public/events`**

Returns occurrences where:
- `night_occurrences.occurrence_date >= today`
- `night_occurrences.status = scheduled`
- `night_series.group.is_public = true`

Ordered by `occurrence_date ASC`. Paginated (`page` / `per_page`, default 20).

Response per occurrence:
```json
{
  "id": "uuid",
  "occurrence_date": "2026-06-14",
  "start_time": "19:00:00",
  "end_time": null,
  "group_name": "The Dice Tower Crew",
  "group_slug": "the-dice-tower-crew",
  "series_title": "Friday Night Games",
  "rsvp_yes_count": 7
}
```

**`GET /api/public/profile/{username}`**

Returns `404` if the user does not exist or if `profile_public = false`.

```json
{
  "username": "apoclyps",
  "display_name": "Kyle",
  "bio": "Eurogame enthusiast. Wingspan evangelist.",
  "avatar_url": "https://....supabase.co/storage/v1/object/public/avatars/uuid",
  "member_since": "2026-05-09",
  "stats_public": true,
  "stats": {
    "total_games_played": 0,
    "total_plays": 0,
    "games_owned": 2
  }
}
```

The `stats` block is always returned as zeros until todo 12 is implemented; the field is present so the frontend can render the stats panel without a schema change later.

### Authenticated routes (new or extended)

| Method | Path | Description |
|---|---|---|
| POST | `/api/users/me/avatar` | Upload avatar (multipart/form-data) |
| PATCH | `/api/users/me` (extend) | Accept `profile_public`, `stats_public`, `display_name`, `bio` |
| PATCH | `/api/groups/{id}` (extend) | Accept `is_public` in the update schema |

**`POST /api/users/me/avatar`**

- Content-Type: `multipart/form-data`
- Field: `file` (the image)
- Returns: updated `UserResponse` (including new `avatar_url`)
- Returns `400` for invalid type or size exceeded
- Returns `502` if Supabase Storage upload fails (with a human-readable message)

---

## Frontend

### New pages

#### `/explore` — Discover upcoming games nights

- No auth required (`meta: { layout: "none" }` or a minimal layout)
- Fetches `GET /api/public/events`
- Grid of event cards, each showing:
  - Group name + series title
  - Date and time
  - RSVP count ("7 going")
  - "View night" link → `/events/{occurrence_id}`
- Empty state: "No public games nights scheduled yet. Start one!"
- Header CTA: "Organise your own → Sign up"
- Pagination / infinite scroll for more events

#### `/events/:id` — Public occurrence detail

- No auth required
- Fetches `GET /api/public/events/{occurrence_id}`
- Shows: date, time, group name, series title, RSVP counts (yes count only — no attendee names for privacy)
- CTA: "Want to RSVP? Sign in or create an account"
- If the occurrence has an active guest token: show the guest RSVP link (this is the same `/rsvp/:token` page already built in Phase 2)

#### `/users/:username` — Public profile

- No auth required
- Fetches `GET /api/public/profile/{username}`
- On `404`: shows "This profile is private" message — does not reveal whether the user exists
- Shows:
  - Avatar (circular, 96 px) — falls back to initials avatar if no `avatar_url`
  - Display name (or username if no display name)
  - Bio
  - Member since date
  - Stats panel (if `stats_public = true`): total games played, total plays, games owned — all zero until todo 12
- "This is you" link to edit profile if the viewer is logged in as this user

### Updated pages

#### `/profile` — My profile (authenticated)

Add a new **Settings** section to the existing ProfilePage:

- **Avatar upload**
  - Circular avatar preview (96 px), initials fallback
  - "Change photo" button triggers a file input (`accept="image/jpeg,image/png,image/webp"`, max 2 MB enforced client-side before upload)
  - Upload progress indicator; on success replace avatar preview with new CDN URL
  - Error if file too large or wrong type

- **Profile visibility**
  - Toggle: "Public profile" (default on) — when on, anyone can view `/users/:username`
  - Toggle: "Public stats" (default on) — when on, play/collection stats are shown on the public profile; only shown if profile is already public

- **About me**
  - `display_name` input (max 100 chars)
  - `bio` textarea (max 500 chars)
  - These were already in the schema but had no edit UI

#### Group settings

Add an **"Open to the public"** toggle to the group management page (`GroupPage.vue`):
- Visible to organisers only
- When on, the group's upcoming nights appear on `/explore`
- Descriptive subtitle: "Upcoming nights will be listed on the public explore page"

### Navigation

Add an **"Explore"** link in the public nav (not behind auth) — visible in the header even when logged out. For the existing `AppShell.vue`, add it to the sidebar. For unauthenticated visitors landing on `/explore`, a minimal top bar with "Sign in" and "Create account" links is sufficient (the `layout: "none"` pages can render their own minimal nav).

---

## Acceptance Criteria

### Backend

- [ ] Migration 006 adds `profile_public` (bool, default true) and `stats_public` (bool, default true) to `users`; migration is reversible
- [ ] `GET /api/public/events` returns only occurrences from groups where `is_public = true`, `occurrence_date >= today`, `status = scheduled`; unauthenticated requests succeed (no auth dependency)
- [ ] `GET /api/public/profile/{username}` returns `404` for both non-existent users and users with `profile_public = false` (no information leakage)
- [ ] `POST /api/users/me/avatar` rejects files > 2 MB with `400`
- [ ] `POST /api/users/me/avatar` rejects non-image MIME types with `400`
- [ ] `POST /api/users/me/avatar` writes to Supabase Storage and updates `users.avatar_url` atomically (if Storage upload fails, the DB row is not updated)
- [ ] `PATCH /api/users/me` accepts and validates `profile_public`, `stats_public`, `display_name` (max 100), `bio` (max 500)
- [ ] `PATCH /api/groups/{id}` accepts `is_public` in the update body (organiser only)

### Frontend

- [ ] `/explore` loads without authentication; shows a "Sign in" CTA in the header
- [ ] `/explore` shows an empty state when no public events exist
- [ ] `/users/:username` shows "This profile is private or does not exist" on 404 — same message for both cases
- [ ] Avatar upload on profile page enforces 2 MB limit client-side before sending the request
- [ ] Avatar upload shows a loading state and replaces the preview on success
- [ ] Profile visibility toggles call `PATCH /api/users/me` on change and show a saved confirmation
- [ ] Group "open to the public" toggle calls `PATCH /api/groups/{id}` and immediately reflects the change
- [ ] `/users/:username` "This is you" link only renders when the logged-in user's username matches

### Tests (`tests/test_public_pages.py`)

- [ ] `GET /api/public/events` returns events from public groups, not from private groups
- [ ] `GET /api/public/events` excludes past occurrences and non-scheduled statuses
- [ ] `GET /api/public/profile/:username` returns 404 for private profiles
- [ ] `GET /api/public/profile/:username` returns 404 for non-existent users (same status code — no leakage)
- [ ] Avatar upload with oversized file returns 400
- [ ] Avatar upload with invalid MIME type returns 400
- [ ] `PATCH /api/users/me` with `profile_public = false` causes subsequent `/api/public/profile/:username` to return 404

---

## Implementation Notes

- Put the public routes in a new `backend/app/api/public.py` router (no `Depends(get_current_user)`); register it at `/api/public` in `main.py`
- The avatar upload endpoint needs `from fastapi import File, UploadFile` and `python-multipart` in requirements
- Supabase Storage API call from Python: `PUT https://{SUPABASE_URL}/storage/v1/object/avatars/{user_id}` with header `Authorization: Bearer {SUPABASE_SERVICE_KEY}` and the raw image bytes as the body; use `httpx` (already available as an asyncio-compatible HTTP client) to make the request from the async FastAPI handler
- The CDN URL includes no cache-buster; because the path is static per user (`avatars/{user_id}`) a new upload overwrites the file but the CDN may serve a stale copy for up to the cache TTL. Add `?t={timestamp}` to the stored URL on each upload to force CDN invalidation — store this timestamped URL in `avatar_url`
- The `/explore` and `/users/:username` pages use `layout: "none"` with their own minimal nav; do not add `requiresAuth` so they load for unauthenticated visitors. The Vue Router guard already allows unauthenticated access to routes without `requiresAuth`
- The stats block in `GET /api/public/profile/:username` returns zeros now and is filled in when todo 12 is implemented; this avoids a breaking API change later
