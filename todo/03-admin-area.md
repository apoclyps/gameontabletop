# Admin Area (`/admin`)

## Goal

Implement a protected admin area accessible only to users with the `admin` role. Unauthorised users attempting to reach any `/admin` route are redirected to the home page (or shown a 403).

## Background

The frontend router (`frontend/src/router/index.js`) already has a `requiresAuth` meta pattern for authenticated-only routes. The backend FastAPI app (`backend/app/main.py`) uses a shared `api_router`. Both need extending to support a second access tier: admin-only.

This todo depends on **04-admin-role.md** — the `is_admin` flag on the user model must exist before this work can be completed.

## Acceptance Criteria

### Frontend

- [ ] A new route `/admin` renders an `AdminPage.vue` component
- [ ] Child routes under `/admin/*` exist for each admin section (e.g. `/admin/users`)
- [ ] Routes under `/admin` carry `meta: { requiresAdmin: true }`
- [ ] The router guard in `router/index.js` checks `requiresAdmin` and redirects non-admin users to `/` with a toast or notification
- [ ] The admin nav is not visible in the UI for non-admin users
- [ ] The `AdminPage.vue` shows a dashboard with placeholder cards for each admin section

### Backend

- [ ] A new router `backend/app/api/admin.py` is mounted at `/api/admin`
- [ ] Every endpoint in the admin router requires the `admin` role (enforced via a FastAPI dependency, e.g. `Depends(require_admin)`)
- [ ] A `GET /api/admin/users` endpoint returns a paginated list of all users (id, email, is_admin, created_at)
- [ ] Requests from non-admin authenticated users receive `403 Forbidden`
- [ ] Requests from unauthenticated users receive `401 Unauthorized`

### Tests

- [ ] Backend: tests in `tests/test_admin.py` cover 200, 401, and 403 cases for each endpoint
- [ ] Frontend: the router guard logic is unit-tested

## Implementation Notes

- Reuse the existing `get_current_user` dependency from `backend/app/dependencies.py` as the base; layer a `require_admin` dependency on top that raises `HTTPException(403)` if `current_user.is_admin` is `False`
- The frontend guard should read admin status from the JWT claims or a `/api/users/me` response stored in app state — avoid a second network request on every navigation
- Do not expose raw database IDs in the admin API; use the same UUID pattern the user API already uses
