# Username Login and Magic Link Authentication

## Goal

Allow users to sign in with their username as an alternative to their email address, and add a passwordless magic link flow so users who forget their password — or simply prefer not to use one — can authenticate via a one-time link sent to their email.

## Background

The current auth implementation (`backend/app/api/auth.py`) accepts only `email + password` at `POST /api/auth/login`. The `LoginRequest` schema has a single `email` field. The frontend `LoginPage.vue` labels the field "Email" and `auth.js` sends `{ email, password }`.

The existing token infrastructure in `backend/app/services/auth.py` uses signed JWTs with a `type` claim (`access`, `refresh`, `verify`, `reset`). Magic link tokens cannot safely reuse this stateless pattern because they must be single-use — a replayed JWT would otherwise be valid until expiry. A separate database-backed token table is required.

Both features share the same login entry point; they are one todo because the `identifier` field change is a prerequisite for magic link (the magic link request must also accept username or email).

---

## Part 1: Username Login

### What changes

The `LoginRequest` Pydantic schema replaces the `email: EmailStr` field with `identifier: str` — a value that is either a valid email address or a username. The login route resolves whichever was provided.

### Backend changes

**`backend/app/schemas/auth.py`** — replace `LoginRequest.email` with `identifier`:

```python
class LoginRequest(BaseModel):
    identifier: str          # email address or username
    password: str
```

**`backend/app/api/auth.py`** — update the login query to match on either column:

```python
result = await session.execute(
    select(User).where(
        (User.email == body.identifier) | (User.username == body.identifier)
    )
)
```

No other backend files change. The response shape (`TokenResponse`) is unchanged.

### Frontend changes

**`frontend/src/services/auth.js`** — rename the `email` parameter to `identifier` in the `login()` call:

```js
export async function login(identifier, password) {
  const res = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
  ...
}
```

**`frontend/src/pages/LoginPage.vue`**:
- Change the `<label>` text from "Email" to "Email or username"
- Change `type="email"` to `type="text"` on the input (since usernames are not email addresses)
- Change `autocomplete="email"` to `autocomplete="username"` (the browser autocomplete hint for a combined identifier field)
- Update the `v-model` binding from `email` to `identifier`

### Acceptance Criteria

- [ ] `POST /api/auth/login` with a valid email + password returns `200` (unchanged behaviour)
- [ ] `POST /api/auth/login` with a valid username + password returns `200`
- [ ] `POST /api/auth/login` with an unknown identifier returns `401` (same message as wrong password — do not reveal whether the identifier exists)
- [ ] `POST /api/auth/login` with a correct identifier but wrong password returns `401`
- [ ] Unverified or inactive account still returns `403` (unchanged behaviour)
- [ ] The frontend input field accepts both email and username without browser validation errors
- [ ] Existing test `TestLogin.test_unknown_email` is updated to `test_unknown_identifier` and a sibling test `test_login_by_username` is added

---

## Part 2: Magic Link Authentication

### Flow

```
1. User clicks "Sign in with a magic link" on the login page
2. User enters their email or username and clicks "Send link"
3. Backend: look up user, create a single-use token, email the link
4. User clicks the link in their email → /auth/magic-link?token=<raw_token>
5. Frontend MagicLinkVerifyPage calls POST /api/auth/magic-link/verify
6. Backend: validate token, mark it used, return access_token + refresh_token
7. Frontend stores tokens and redirects to /dashboard
```

### Data Model

**New table: `magic_link_tokens`**

Raw tokens are never stored. Only a SHA-256 hash of the raw token is persisted so a database breach does not yield usable tokens.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| token_hash | varchar(64) | hex-encoded SHA-256 of the raw token |
| expires_at | timestamptz | 15 minutes from creation |
| used_at | timestamptz nullable | set on first successful exchange; null = unused |
| created_at | timestamptz | |
| INDEX | (token_hash) | for fast lookup on verify |
| INDEX | (user_id, created_at DESC) | for rate-limit and cleanup queries |

An Alembic migration creates this table. The migration is reversible.

### Token generation

Generate the raw token as a 32-byte cryptographically random URL-safe string (`secrets.token_urlsafe(32)`). Hash it with SHA-256 before storage. Send the raw token in the email link only; never log or return it from the API.

```python
import hashlib, secrets

def generate_magic_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed
```

### Rate limiting

To prevent the endpoint from being used to send spam, enforce a per-user rate limit:

- Maximum 3 magic link requests per user per 10 minutes
- Check by counting `magic_link_tokens WHERE user_id = :id AND created_at > now() - interval '10 minutes'`
- Return `429 Too Many Requests` with a `Retry-After` header if the limit is exceeded
- Always return `200` for unknown identifiers (same anti-enumeration pattern as `POST /api/auth/forgot-password`)

### API routes

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/magic-link` | public | Request a magic link |
| POST | `/api/auth/magic-link/verify` | public | Exchange a raw token for access + refresh tokens |

**`POST /api/auth/magic-link` request:**

```json
{ "identifier": "alice@example.com" }
```

- Accepts email or username (same `identifier` pattern as the updated login endpoint)
- Returns `200` with `{"message": "If that account exists, a sign-in link has been sent."}` in all cases
- Does not reveal whether the account exists

**`POST /api/auth/magic-link/verify` request:**

```json
{ "token": "<raw_token>" }
```

- Hash the submitted token with SHA-256, look up `magic_link_tokens WHERE token_hash = :hash`
- Return `400` if not found, already used (`used_at IS NOT NULL`), or expired (`expires_at < now()`)
- On success: set `used_at = now()`, return `TokenResponse` (same shape as password login)
- Verify the linked user is active and verified before issuing tokens; return `403` if not

### Email

Add a `send_magic_link_email(email: str, token: str)` function to `backend/app/services/email.py`, following the same pattern as `send_password_reset_email`. The link in the email points to the frontend:

```
https://gameontabletop.com/auth/magic-link?token=<raw_token>
```

Subject: "Your Game On Tabletop sign-in link"
Body: "Click the link below to sign in. This link expires in 15 minutes and can only be used once."

### Frontend changes

**`frontend/src/pages/LoginPage.vue`**:
- Add a "Sign in with a magic link" link below the password form, styled as a secondary action
- Clicking it does not navigate away — it toggles to a magic link sub-form (email/username field + "Send link" button) within the same card, replacing the password form
- A "Use password instead" link toggles back
- Success state after sending: replace the form with "Check your email — we've sent a sign-in link. It expires in 15 minutes."

**New page: `frontend/src/pages/MagicLinkVerifyPage.vue`**:
- Route: `/auth/magic-link` with `meta: { guestOnly: true }`
- On mount, reads `?token=` from the URL query string and immediately calls `POST /api/auth/magic-link/verify`
- Loading state: "Signing you in…" spinner
- Success: stores tokens and redirects to `/dashboard`
- Error (invalid/expired/used token): shows a clear message and a "Request a new link" button that navigates back to `/login` with the magic link sub-form open

**`frontend/src/services/auth.js`** — add:

```js
export async function requestMagicLink(identifier) { ... }
export async function verifyMagicLink(token) { ... }
```

### Acceptance Criteria

#### Backend

- [ ] Alembic migration creates `magic_link_tokens` with correct indexes; migration is reversible
- [ ] Raw token is never stored; only the SHA-256 hex digest is written to the database
- [ ] `POST /api/auth/magic-link` always returns `200` regardless of whether the identifier matches an account
- [ ] Rate limit of 3 requests per 10 minutes per user is enforced; `429` returned on breach
- [ ] `POST /api/auth/magic-link/verify` returns `400` for unknown, used, or expired tokens
- [ ] A used token cannot be reused — `used_at` is set atomically with the token response; a second call with the same raw token returns `400`
- [ ] Tokens expire after exactly 15 minutes; a token used at minute 14 succeeds; a token used at minute 16 fails
- [ ] The linked user must be active and verified to receive a token response; inactive/unverified users get `403`
- [ ] A Vercel Cron job (or the existing nightly cron) purges `magic_link_tokens WHERE expires_at < now() - interval '1 day'` to prevent unbounded table growth

#### Frontend

- [ ] The magic link sub-form is accessible without a page navigation (toggled in place on the login card)
- [ ] The "Send link" button shows a loading state and is disabled after submission to prevent double-sends
- [ ] `MagicLinkVerifyPage.vue` handles the token exchange on mount without requiring user interaction
- [ ] An expired or used token shows a user-friendly error with a clear call to action — not a generic "Something went wrong"
- [ ] The `/auth/magic-link` route is `guestOnly`; an already-authenticated user visiting it is redirected to `/dashboard`

### Tests

Add to `tests/test_auth.py`:

```
class TestUsernameLogin:
    test_login_by_username            # success
    test_login_by_email               # existing success case renamed for clarity
    test_unknown_identifier_returns_401
    test_username_wrong_password_returns_401

class TestMagicLink:
    test_request_always_200_for_unknown_identifier
    test_request_sends_email_for_known_user
    test_verify_success_returns_tokens
    test_verify_used_token_returns_400
    test_verify_expired_token_returns_400
    test_verify_unknown_token_returns_400
    test_verify_inactive_user_returns_403
    test_rate_limit_after_3_requests
    test_rate_limit_resets_after_10_minutes
```

---

## Implementation Notes

- The `magic_link_tokens` table is intentionally separate from the JWT token infrastructure in `app/services/auth.py`. Do not add a `magic` type to the existing `_create_token` function — stateless JWTs cannot be invalidated after single use
- When adding the `MagicLinkVerifyPage.vue` route, add it to `router/index.js` as a `guestOnly` route so authenticated users aren't redirected to it from external links after already signing in
- The 15-minute expiry is intentionally short. If users complain, it can be extended to 30 minutes, but do not go beyond 60 minutes — magic links are effectively temporary passwords and should behave like them
- Do not silently merge the magic link flow with the existing `forgot-password` flow. They are semantically different: forgot-password is a recovery path for users who have a password but cannot remember it; magic link is a primary authentication method for users who prefer it. Conflating them causes confusing UX
- Clean up expired magic link tokens in the same nightly Cron endpoint that handles occurrence generation and reminder sending (Phase 4 of the main plan), rather than adding a dedicated cleanup endpoint
