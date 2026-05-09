from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def no_email():
    with patch("app.api.auth.send_verification_email"):
        yield


async def _setup(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "username": "testuser", "password": "Password1"},
    )
    from app.services.auth import create_verification_token
    token = create_verification_token("user@example.com")
    await client.get(f"/api/auth/verify-email?token={token}")
    login = await client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "Password1"},
    )
    return login.json()["access_token"]


class TestGetProfile:
    async def test_authenticated(self, client: AsyncClient):
        token = await _setup(client)
        r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "user@example.com"
        assert data["username"] == "testuser"
        assert data["is_verified"] is True

    async def test_unauthenticated(self, client: AsyncClient):
        r = await client.get("/api/users/me")
        assert r.status_code in (401, 403)


class TestUpdateProfile:
    async def test_update_fields(self, client: AsyncClient):
        token = await _setup(client)
        r = await client.patch(
            "/api/users/me",
            json={"display_name": "Test User", "bio": "Hello world"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["display_name"] == "Test User"
        assert data["bio"] == "Hello world"

    async def test_partial_update(self, client: AsyncClient):
        token = await _setup(client)
        r = await client.patch(
            "/api/users/me",
            json={"display_name": "Only Name"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["display_name"] == "Only Name"
        assert r.json()["bio"] is None

    async def test_unauthenticated(self, client: AsyncClient):
        r = await client.patch("/api/users/me", json={"display_name": "X"})
        assert r.status_code in (401, 403)
