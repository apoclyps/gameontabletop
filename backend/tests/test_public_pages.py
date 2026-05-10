import io
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.group import Group, GroupMember
from app.models.scheduler import NightOccurrence, NightSeries
from app.models.user import User


@pytest.fixture(autouse=True)
def no_email():
    with patch("app.api.auth.send_verification_email"):
        yield


async def _register_login(client, email="u@test.com", username="testuser", password="Passw0rd!"):
    await client.post("/api/auth/register", json={"email": email, "username": username, "password": password})
    from app.services.auth import create_verification_token
    token = create_verification_token(email)
    await client.get(f"/api/auth/verify-email?token={token}")
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _create_group_series_occurrence(client, db_session, token, *, is_public=True, occurrence_date=None, status="scheduled"):
    import uuid as _uuid

    g = await client.post("/api/groups", json={"name": "Test Group", "is_public": is_public}, headers=_auth(token))
    group_id = _uuid.UUID(g.json()["id"])

    result = await db_session.execute(select(User))
    user = result.scalars().first()

    series = NightSeries(
        group_id=group_id,
        title="Friday Games",
        recurrence="weekly",
        default_start_time=time(19, 0),
        created_by=user.id,
    )
    db_session.add(series)
    await db_session.flush()

    occ_date = occurrence_date or (date.today() + timedelta(days=7))
    occ = NightOccurrence(
        series_id=series.id,
        occurrence_date=occ_date,
        start_time=time(19, 0),
        status=status,
    )
    db_session.add(occ)
    await db_session.commit()
    return str(group_id), str(series.id), str(occ.id)


class TestPublicEvents:
    async def test_returns_events_from_public_groups(self, client: AsyncClient, db_session):
        token = await _register_login(client)
        await _create_group_series_occurrence(client, db_session, token, is_public=True)

        r = await client.get("/api/public/events")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["series_title"] == "Friday Games"

    async def test_excludes_private_groups(self, client: AsyncClient, db_session):
        token = await _register_login(client)
        await _create_group_series_occurrence(client, db_session, token, is_public=False)

        r = await client.get("/api/public/events")
        assert r.status_code == 200
        assert r.json() == []

    async def test_excludes_past_occurrences(self, client: AsyncClient, db_session):
        token = await _register_login(client)
        past = date.today() - timedelta(days=1)
        await _create_group_series_occurrence(client, db_session, token, is_public=True, occurrence_date=past)

        r = await client.get("/api/public/events")
        assert r.status_code == 200
        assert r.json() == []

    async def test_excludes_non_scheduled_status(self, client: AsyncClient, db_session):
        token = await _register_login(client)
        await _create_group_series_occurrence(client, db_session, token, is_public=True, status="cancelled")

        r = await client.get("/api/public/events")
        assert r.status_code == 200
        assert r.json() == []

    async def test_no_auth_required(self, client: AsyncClient):
        r = await client.get("/api/public/events")
        assert r.status_code == 200


class TestPublicProfile:
    async def test_returns_public_profile(self, client: AsyncClient):
        token = await _register_login(client)
        r = await client.get("/api/public/profile/testuser")
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "testuser"
        assert data["stats_public"] is True

    async def test_404_for_nonexistent_user(self, client: AsyncClient):
        r = await client.get("/api/public/profile/nobody")
        assert r.status_code == 404

    async def test_404_for_private_profile(self, client: AsyncClient):
        token = await _register_login(client)
        await client.patch(
            "/api/users/me",
            json={"profile_public": False},
            headers=_auth(token),
        )
        r = await client.get("/api/public/profile/testuser")
        assert r.status_code == 404

    async def test_same_404_for_private_and_nonexistent(self, client: AsyncClient):
        token = await _register_login(client)
        await client.patch("/api/users/me", json={"profile_public": False}, headers=_auth(token))
        r_private = await client.get("/api/public/profile/testuser")
        r_missing = await client.get("/api/public/profile/nobody")
        assert r_private.status_code == r_missing.status_code == 404

    async def test_no_auth_required(self, client: AsyncClient):
        await _register_login(client)
        r = await client.get("/api/public/profile/testuser")
        assert r.status_code == 200


class TestAvatarUpload:
    async def test_rejects_oversized_file(self, client: AsyncClient):
        token = await _register_login(client)
        big = b"x" * (2 * 1024 * 1024 + 1)
        r = await client.post(
            "/api/users/me/avatar",
            files={"file": ("photo.jpg", io.BytesIO(big), "image/jpeg")},
            headers=_auth(token),
        )
        assert r.status_code == 400
        assert "2 MB" in r.json()["detail"]

    async def test_rejects_invalid_mime_type(self, client: AsyncClient):
        token = await _register_login(client)
        r = await client.post(
            "/api/users/me/avatar",
            files={"file": ("doc.pdf", io.BytesIO(b"data"), "application/pdf")},
            headers=_auth(token),
        )
        assert r.status_code == 400

    async def test_requires_auth(self, client: AsyncClient):
        r = await client.post(
            "/api/users/me/avatar",
            files={"file": ("photo.jpg", io.BytesIO(b"data"), "image/jpeg")},
        )
        assert r.status_code in (401, 403)

    async def test_successful_upload_updates_avatar_url(self, client: AsyncClient):
        token = await _register_login(client)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.put = AsyncMock(return_value=mock_response)

        with patch("app.api.users.settings") as mock_settings, patch("app.api.users.httpx.AsyncClient", return_value=mock_client):
            mock_settings.supabase_url = "https://test.supabase.co"
            mock_settings.supabase_service_role_key = "service-key"

            r = await client.post(
                "/api/users/me/avatar",
                files={"file": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff" + b"0" * 100), "image/jpeg")},
                headers=_auth(token),
            )

        assert r.status_code == 200
        data = r.json()
        assert data["avatar_url"] is not None
        assert "supabase.co" in data["avatar_url"]


class TestProfilePublicToggle:
    async def test_patch_profile_public_false_hides_public_profile(self, client: AsyncClient):
        token = await _register_login(client)

        r = await client.get("/api/public/profile/testuser")
        assert r.status_code == 200

        await client.patch("/api/users/me", json={"profile_public": False}, headers=_auth(token))

        r = await client.get("/api/public/profile/testuser")
        assert r.status_code == 404
