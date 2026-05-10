# Calendar and Messaging Integrations

## Goal

Let users and groups connect Game On Tabletop to the tools they already live in — Google Calendar for scheduling, Discord for group chat, and WhatsApp for mobile coordination — so that reminders and updates reach people without requiring them to open the app.

## Background

The plan already covers email notifications via SendGrid and has a placeholder for iCal export (`GET /api/occurrences/{id}/calendar.ics` in Phase 4). The research document identifies WhatsApp and Discord as the de-facto coordination layer most groups currently use, and the core problem statement is that coordination is fragmented across too many tools. These integrations close that gap.

The three integrations have fundamentally different implementation patterns and friction levels:

- **iCal subscription** — a read-only URL users add to any calendar app; no OAuth, no credentials; ships first as it is already planned
- **Google Calendar push** — OAuth2 so the app can create and update events directly in the user's calendar without them having to subscribe to a feed
- **Discord** — a webhook URL pasted by the group organiser into the app; no bot installation or OAuth required for notifications; an optional bot phase adds interactive RSVP buttons
- **WhatsApp** — Meta WhatsApp Business Cloud API; highest friction (requires business account approval and user opt-in); ships last

All integrations are strictly opt-in. Users who do not connect anything continue to receive email only.

---

## Unified Notification Architecture

Before adding channels, the existing email dispatch logic must be refactored into a unified notification dispatcher so that new channels slot in cleanly.

### Notification event types

Every domain action that should notify anyone maps to a named event type:

| Event type | Triggered by | Affected parties |
|---|---|---|
| `occurrence.scheduled` | Auto-generation or manual creation | All group members |
| `occurrence.reminder` | Cron, 48h before `starts_at` | Members with no RSVP or RSVP = maybe |
| `occurrence.quorum_nudge` | Cron, configurable days before | Organiser |
| `occurrence.cancelled` | Organiser action | All RSVPd members |
| `occurrence.postponed` | Organiser action | All RSVPd members |
| `rsvp.flip_alert` | Member flips In→Out within 24h of session | Organiser |
| `poll.created` | Organiser creates availability poll | All group members |
| `poll.resolved` | Organiser resolves poll | All poll respondents |
| `game_voting.open` | Occurrence `game_vote_deadline` set | yes/maybe RSVPs |
| `session.recap` | Post-session result logged | All group members |
| `open_game.join_confirmed` | Player joins open game | That player |
| `open_game.cancelled` | Host cancels open game | All joined/waitlisted players |
| `loan.requested` | Borrower initiates | Lender |
| `loan.confirmed` | Lender confirms | Borrower |

### Dispatcher contract

Implement `backend/app/services/notifications.py` with a single entry point:

```python
async def dispatch(event_type: str, payload: dict, recipients: list[Recipient]) -> None:
    ...
```

`Recipient` carries the user ID plus the set of enabled channels for that user/event combination. The dispatcher fans out to each channel handler in parallel. Individual channel failures are logged and retried but do not block other channels or raise to the caller.

### Notification preferences

Add a `notification_preferences` table to let users control which events reach which channels:

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| event_type | varchar(50) | matches event type strings above |
| channel | enum(email, google_calendar, discord_dm, whatsapp) | |
| enabled | bool default true | |
| UNIQUE | (user_id, event_type, channel) | one preference per combination |

Sensible defaults on account creation: email enabled for all events; all other channels disabled until the user connects them.

---

## Data Model

### `user_integrations`

Stores per-user OAuth tokens and channel-specific identifiers.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| provider | enum(google_calendar, discord, whatsapp) | |
| status | enum(active, revoked, error) | |
| external_id | varchar nullable | Google user sub, Discord user ID, WhatsApp phone E.164 |
| access_token_enc | text nullable | encrypted; Google Calendar short-lived token |
| refresh_token_enc | text nullable | encrypted; Google Calendar long-lived token |
| token_expires_at | timestamptz nullable | |
| scopes | varchar nullable | space-separated OAuth scopes granted |
| connected_at | timestamptz | |
| last_used_at | timestamptz nullable | |
| UNIQUE | (user_id, provider) | one connection per provider per user |

### `group_integrations`

Stores per-group external service connections (Discord channel webhooks, etc.).

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| group_id | UUID FK → groups | |
| provider | enum(discord_webhook, whatsapp_group) | |
| status | enum(active, revoked, error) | |
| webhook_url_enc | text nullable | encrypted; Discord webhook URL |
| external_id | varchar nullable | WhatsApp group ID |
| label | varchar(100) nullable | human label, e.g. "Saturday Crew Discord" |
| added_by_user_id | UUID FK → users | organiser who connected it |
| connected_at | timestamptz | |
| last_used_at | timestamptz nullable | |
| UNIQUE | (group_id, provider) | one connection per provider per group |

### `google_calendar_events`

Tracks the Google Calendar event IDs the app has created so it can update or delete them later.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_integration_id | UUID FK → user_integrations | |
| occurrence_id | UUID FK → night_occurrences nullable | |
| open_game_id | UUID FK → open_games nullable | |
| google_event_id | varchar | the `id` returned by the Calendar API |
| calendar_id | varchar default 'primary' | which calendar the event lives in |
| synced_at | timestamptz | |

---

## Integration 1: iCal Subscription (ships first)

No OAuth, no credentials. A stable URL that any calendar app can subscribe to and poll.

### API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/series/{id}/calendar.ics` | group member (via token) | iCal feed for all occurrences in a series |
| GET | `/api/users/me/calendar.ics` | API key in query param | Personal feed of all upcoming occurrences across all groups |
| GET | `/api/occurrences/{id}/calendar.ics` | public | Single occurrence iCal file (for sharing) |
| GET | `/api/open-games/{id}/calendar.ics` | public | Single open game iCal file |

- The personal feed URL includes a long-lived opaque token (stored in `user_integrations` as a `provider = ical_feed` entry) so the user can revoke it without changing their password
- iCal events include: title, description with game shortlist, location/address, organiser, and a URL back to the occurrence page
- Occurrence updates (postpone, cancel) are reflected in the feed automatically; subscribed calendars pick up changes on their next poll

### Frontend

- [ ] Settings page (`/settings/integrations`) shows an "Add to Calendar" section with a copyable subscription URL and one-click buttons for Google Calendar, Apple Calendar, and Outlook (deep links to those apps' subscribe-by-URL flows)
- [ ] Each occurrence page has an "Add to Calendar" dropdown with the same options plus a direct `.ics` download

---

## Integration 2: Google Calendar Push

### OAuth2 Flow

- Scopes required: `https://www.googleapis.com/auth/calendar.events` (write events to the user's calendar only; not read)
- Use the standard OAuth2 authorisation code flow; store the refresh token encrypted in `user_integrations`
- On token expiry, refresh silently before the next API call; on `invalid_grant` (revoked), mark integration `status = revoked` and notify the user by email

### Behaviour

- When an occurrence is created or its date/time/location changes, upsert the corresponding Google Calendar event for all group members who have connected Google Calendar and have `occurrence.scheduled` → `google_calendar` enabled
- When an occurrence is cancelled, delete the Google Calendar event
- When a user RSVPs `yes` or `maybe`, create the event in their calendar if not already present
- When a user RSVPs `no`, delete the event from their calendar
- Track created event IDs in `google_calendar_events` so updates and deletes target the correct event

### API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/integrations/google/auth` | required | Redirect to Google OAuth consent screen |
| GET | `/api/integrations/google/callback` | public | OAuth callback; exchanges code for tokens |
| DELETE | `/api/integrations/google` | required | Revoke and disconnect Google Calendar |
| GET | `/api/integrations/google/status` | required | Current connection status and last sync time |

### Acceptance Criteria

- [ ] OAuth flow completes and refresh token is stored AES-256 encrypted using a server-side key from environment config (never stored in plaintext)
- [ ] Revoking via the app calls the Google token revocation endpoint before deleting the local record
- [ ] A background task (Vercel Cron or dispatched via the notification service) handles fan-out to all affected members asynchronously — Google Calendar writes never block the API response
- [ ] If a Google API call fails with a retryable error (429, 503), the task is retried with exponential backoff up to 3 times; after that the integration is marked `status = error` and the user is notified by email
- [ ] Tests mock the Google Calendar API and verify create, update, and delete calls are issued correctly for each trigger event

---

## Integration 3: Discord

### Phase A — Webhook (group-level channel notifications)

The organiser creates a webhook in their Discord server (Server Settings → Integrations → Webhooks), copies the URL, and pastes it into the group settings page. No bot installation, no OAuth.

**Messages are posted as rich embeds:**

- **Session scheduled**: title, date/time, venue, player count, "Is it on?" quorum status, link to RSVP page
- **RSVP reminder** (48h before): current attendance tally, quorum state, link to RSVP
- **Session cancelled / postponed**: clear subject, new date if postponed
- **Quorum borderline alert**: "Only 3/4 confirmed — 2 maybes haven't responded"
- **Game voting open**: shortlisted games with thumbnail images, link to vote
- **Session recap**: games played, winners, attendance count

Discord embed format:
- Colour-coded by status: green (confirmed on), amber (borderline), red (cancelled)
- Footer with the group name and a link to the occurrence page
- Thumbnail: BGG artwork of the first shortlisted game where available

**API**

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/groups/{id}/integrations/discord` | organiser | Save webhook URL |
| DELETE | `/api/groups/{id}/integrations/discord` | organiser | Remove webhook |
| POST | `/api/groups/{id}/integrations/discord/test` | organiser | Send a test message |

**Acceptance Criteria**

- [ ] Webhook URL is validated by sending a test `GET` to Discord before saving; invalid URLs are rejected with a clear error
- [ ] Webhook URL is stored encrypted; it is never returned in API responses (only connection status and label are exposed)
- [ ] Failed webhook posts (Discord returns non-2xx) are retried once after 30 seconds; if still failing, integration is marked `status = error` and the organiser is notified by email
- [ ] The test endpoint posts a clearly labelled "This is a test message from Game On Tabletop" embed

### Phase B — Discord Bot (interactive RSVP, optional)

A Discord bot enables users to RSVP directly from Discord without opening the app. This requires users to link their Discord account via OAuth.

- Bot command `/rsvp yes|no|maybe` in the group's Discord channel — the bot looks up the user's linked account and updates their RSVP
- Bot DMs the user 24h before the session with an RSVP prompt containing Yes/No/Maybe buttons (Discord components)
- Bot posts the session recap automatically after the result is logged

Shipping the bot is a separate, later phase. The webhook approach covers the notification requirement without the added complexity of bot permissions, slash command registration, and user account linking.

---

## Integration 4: WhatsApp

### Prerequisites

WhatsApp requires a verified Meta Business account and a dedicated phone number before any messages can be sent. This is the highest-friction integration and should ship last. The implementation assumes the Meta WhatsApp Business Cloud API (direct, no Twilio intermediary).

**Required setup (done once by the site operator, not per-user):**
1. Create a Meta Business account and verify the business
2. Register a dedicated phone number (cannot be a personal number already on WhatsApp)
3. Submit message templates for approval — outbound business-initiated messages must use pre-approved templates

### User opt-in

WhatsApp policy requires explicit opt-in before the first message. The opt-in flow:
1. User navigates to Settings → Integrations → WhatsApp
2. User enters their mobile number (E.164 format, e.g. +447700900123)
3. App sends a one-time verification code via WhatsApp (using the `authentication` template)
4. User enters the code to confirm their number and consent to notifications
5. Number is stored in `user_integrations` (encrypted); opt-in consent timestamp is recorded for compliance

### Message templates

All outbound messages use Meta-approved templates with variable substitution. Draft templates to submit for approval:

| Template name | Purpose | Sample body |
|---|---|---|
| `session_reminder` | 48h RSVP nudge | "Hey {{1}}, {{2}} is this {{3}} at {{4}}. Are you in? Reply YES, NO, or MAYBE." |
| `quorum_alert` | Borderline attendance | "{{1}} only has {{2}}/{{3}} confirmed for {{4}}. Can you help spread the word?" |
| `session_cancelled` | Cancellation notice | "{{1}} on {{2}} has been cancelled. See you next time!" |
| `session_recap` | Post-session summary | "{{1}} — {{2}} played last night. {{3}} won {{4}}. Full recap: {{5}}" |

### Group WhatsApp (future)

Sending to a WhatsApp group (rather than individual DMs) requires a WhatsApp group link and the business number being a member of that group. This is operationally complex and should be deferred; individual DMs to opted-in users cover the core need.

### API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/integrations/whatsapp/opt-in` | required | Start opt-in; sends verification code |
| POST | `/api/integrations/whatsapp/verify` | required | Submit code to confirm number |
| DELETE | `/api/integrations/whatsapp` | required | Opt out and delete number |

### Acceptance Criteria

- [ ] Phone numbers are stored AES-256 encrypted and never logged or returned in API responses
- [ ] Opt-out immediately removes the number and sets integration `status = revoked`; no further messages are sent
- [ ] Template variable substitution is validated before sending — missing variables raise an error rather than sending a malformed message
- [ ] Inbound replies ("YES", "NO", "MAYBE") to the `session_reminder` template are handled via the Meta webhook and update the user's RSVP in the database
- [ ] The Meta webhook endpoint validates the `X-Hub-Signature-256` header before processing any payload

---

## Frontend — Settings Page (`/settings/integrations`)

- [ ] A dedicated `/settings/integrations` page lists all four integration types with connection status (connected / not connected / error)
- [ ] **iCal**: shows the subscription URL with a copy button and deep-link buttons for major calendar apps; a "Regenerate link" button invalidates the old token
- [ ] **Google Calendar**: "Connect Google Calendar" button starts the OAuth flow; connected state shows the linked Google account email and a "Disconnect" button
- [ ] **Discord** (group-level, shown within group settings at `/groups/{id}/settings`): webhook URL input, label field, test button, current status badge
- [ ] **WhatsApp**: phone number input with country code selector, verification code input, opt-out button; clearly states what messages will be sent before opt-in
- [ ] **Notification preferences** table: matrix of event types × channels with toggle switches; defaults pre-populated; changes save immediately via PATCH with a success toast

---

## Implementation Notes

- Encrypt all credentials at rest using AES-256-GCM with a key from environment config (`ENCRYPTION_KEY`); use a library such as `cryptography` (Python) rather than implementing encryption manually
- The notification dispatcher (`backend/app/services/notifications.py`) must be the single place where channel fan-out logic lives — do not add Discord or WhatsApp calls directly inside route handlers or Cron handlers
- Vercel's serverless environment has no persistent workers; all async notification tasks must be either: (a) dispatched synchronously within the request if fast enough (Discord webhook post is typically < 200ms), or (b) offloaded to a Vercel Cron endpoint for bulk fan-out (RSVP reminders to all members of all groups)
- Test the notification dispatcher with a mock channel registry so unit tests verify routing logic without making real HTTP calls to Google, Discord, or Meta
- Rate limits to respect: Google Calendar API (1M queries/day — not a concern), Discord webhooks (5 requests/2 seconds per webhook — batch group notifications), Meta Cloud API (1000 messages/day on free tier, scales with business tier)
- iCal feeds should set `Cache-Control: no-cache` so calendar clients always fetch the latest; include `SEQUENCE` and `LAST-MODIFIED` fields in each `VEVENT` so clients can detect updates
