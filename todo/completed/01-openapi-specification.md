# OpenAPI Specification for Endpoints

## Goal

Produce a complete, accurate OpenAPI 3.x specification for all backend API endpoints so that consumers (frontend, third-party integrators, automated tests) have a single source of truth for the contract.

## Background

FastAPI generates an OpenAPI schema automatically from route definitions, Pydantic models, and docstrings. The current routes (`/api/auth/*`, `/api/users/*`, `/api/health`) are functional but lack:

- Explicit response models on every route
- Documented error responses (401, 403, 404, 422)
- Meaningful `summary` and `description` strings
- Security scheme declarations (Bearer JWT)
- Tags that group routes logically in the rendered UI

## Acceptance Criteria

- [ ] Every route has an explicit `response_model` or `responses` dict
- [ ] Every route has a `summary` and, where non-trivial, a `description`
- [ ] Auth-protected routes declare the `HTTPBearer` security scheme
- [ ] Error responses (401, 403, 404, 422) are documented with example bodies
- [ ] Routes are tagged (`auth`, `users`, `admin`) so the Swagger UI groups them
- [ ] The generated spec passes `openapi-spec-validator` with zero errors
- [ ] A `GET /api/openapi.json` endpoint is accessible (FastAPI provides this by default — verify it is not blocked in production)
- [ ] The spec is also exported as a static file (`openapi.yaml`) committed to the repo for offline consumption and CI diffing

## Implementation Notes

- Add `response_model` to each router function in `backend/app/api/auth.py` and `backend/app/api/users.py`
- Declare a reusable `HTTPBearer` security scheme in `app/main.py` via `FastAPI(... openapi_extra=...)`  or via `SecurityBase` dependencies
- Use `responses={401: {"description": "Unauthorized"}, ...}` on individual routes
- Export the spec via a CI step: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > openapi.json`
- Add `openapi-spec-validator` to dev dependencies and run it in the PR checks workflow (`.github/workflows/pr-checks.yml`)
