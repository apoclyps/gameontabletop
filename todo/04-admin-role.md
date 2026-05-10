# Admin Role on Users

## Goal

Add an `is_admin` boolean field to the user model so that certain users can be granted elevated permissions for site management. This is the data-layer prerequisite for the admin area (see `03-admin-area.md`).

## Background

The users table is managed via Alembic migrations (`backend/alembic/versions/002_create_users.py`). The user model and schemas live in `backend/app/` and are exposed through the `/api/users` router. Adding an admin role requires a migration, model update, and careful access controls to prevent privilege escalation.

## Acceptance Criteria

### Database

- [ ] A new Alembic migration adds `is_admin BOOLEAN NOT NULL DEFAULT FALSE` to the `users` table
- [ ] The migration is reversible (downgrade drops the column)
- [ ] Existing rows default to `is_admin = FALSE` with no data loss

### Backend

- [ ] The `User` SQLAlchemy model includes `is_admin: bool`
- [ ] The `UserResponse` Pydantic schema exposes `is_admin` so clients know the caller's role
- [ ] The `UserCreate` / `UserUpdate` schemas do **not** allow `is_admin` to be set via the public API — only a privileged internal operation or direct DB seed may set it
- [ ] A `GET /api/users/me` response includes `is_admin` in the payload
- [ ] A `PATCH /api/admin/users/{user_id}/role` endpoint (admin-only) allows an admin to toggle another user's `is_admin` flag
- [ ] An admin cannot demote themselves (prevents lockout)

### Seeding

- [ ] A seed script or management command (`scripts/create_admin.py`) allows a developer to promote an existing user to admin via the CLI: `python scripts/create_admin.py <email>`

### Tests

- [ ] Migration round-trip test (upgrade + downgrade) passes
- [ ] `test_users.py` covers that `is_admin` cannot be set via `POST /api/auth/register` or `PATCH /api/users/me`
- [ ] `test_admin.py` covers the role-toggle endpoint (success, self-demotion blocked, 403 for non-admins)

## Implementation Notes

- `is_admin` should live on the core `users` table rather than a separate roles table — the site currently needs only two tiers (user / admin). A full RBAC system can be introduced later if requirements grow.
- The JWT payload should include `is_admin` as a claim so the frontend can gate the admin UI without an extra API call. Re-issue tokens on role change or instruct the user to re-login.
- Protect the seed script from being called in production environments by checking `settings.environment != "production"` before executing.
