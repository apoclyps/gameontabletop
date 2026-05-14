from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def no_email():
    with (
        patch("app.api.auth.send_verification_email"),
        patch("app.api.auth.send_password_reset_email"),
    ):
        yield


async def register(
    client: AsyncClient,
    email="user@example.com",
    username="testuser",
    password="Password1",
):
    return await client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )


async def verify(client: AsyncClient, email="user@example.com"):
    from app.services.auth import create_verification_token

    token = create_verification_token(email)
    return await client.get(f"/api/auth/verify-email?token={token}")


async def register_and_verify(
    client: AsyncClient, email="user@example.com", username="testuser"
):
    await register(client, email=email, username=username)
    await verify(client, email=email)


class TestRegister:
    async def test_success(self, client: AsyncClient):
        r = await register(client)
        assert r.status_code == 201
        assert "Registration successful" in r.json()["message"]

    async def test_duplicate_email(self, client: AsyncClient):
        await register(client)
        r = await register(client, username="other")
        assert r.status_code == 409

    async def test_duplicate_username(self, client: AsyncClient):
        await register(client)
        r = await register(client, email="other@example.com")
        assert r.status_code == 409

    async def test_short_password(self, client: AsyncClient):
        r = await register(client, password="short")
        assert r.status_code == 422

    async def test_invalid_username(self, client: AsyncClient):
        r = await register(client, username="bad username!")
        assert r.status_code == 422


class TestVerifyEmail:
    async def test_success(self, client: AsyncClient):
        await register(client)
        r = await verify(client)
        assert r.status_code == 200

    async def test_invalid_token(self, client: AsyncClient):
        r = await client.get("/api/auth/verify-email?token=badtoken")
        assert r.status_code == 400

    async def test_wrong_token_type(self, client: AsyncClient):
        from app.services.auth import create_access_token

        token = create_access_token("fake-id")
        r = await client.get(f"/api/auth/verify-email?token={token}")
        assert r.status_code == 400


class TestLogin:
    async def test_success(self, client: AsyncClient):
        await register_and_verify(client)
        r = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "Password1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_wrong_password(self, client: AsyncClient):
        await register_and_verify(client)
        r = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "wrongpass"},
        )
        assert r.status_code == 401

    async def test_unverified(self, client: AsyncClient):
        await register(client)
        r = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "Password1"},
        )
        assert r.status_code == 403

    async def test_unknown_email(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/login", json={"email": "no@example.com", "password": "Password1"}
        )
        assert r.status_code == 401


class TestRefresh:
    async def test_success(self, client: AsyncClient):
        await register_and_verify(client)
        login = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "Password1"},
        )
        refresh_token = login.json()["refresh_token"]
        r = await client.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert r.status_code == 200
        assert "access_token" in r.json()

    async def test_invalid_token(self, client: AsyncClient):
        r = await client.post("/api/auth/refresh", json={"refresh_token": "bad"})
        assert r.status_code == 401

    async def test_access_token_rejected(self, client: AsyncClient):
        await register_and_verify(client)
        login = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "Password1"},
        )
        access_token = login.json()["access_token"]
        r = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
        assert r.status_code == 401


class TestForgotPassword:
    async def test_known_email_always_200(self, client: AsyncClient):
        await register_and_verify(client)
        r = await client.post(
            "/api/auth/forgot-password", json={"email": "user@example.com"}
        )
        assert r.status_code == 200

    async def test_unknown_email_still_200(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/forgot-password", json={"email": "nobody@example.com"}
        )
        assert r.status_code == 200


class TestResetPassword:
    async def test_success(self, client: AsyncClient):
        await register_and_verify(client)
        from app.services.auth import create_password_reset_token, decode_token

        login = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "Password1"},
        )
        access = login.json()["access_token"]
        payload = decode_token(access)
        token = create_password_reset_token(payload["sub"])
        r = await client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert r.status_code == 200
        # Login with new password
        r2 = await client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "NewPass123"},
        )
        assert r2.status_code == 200

    async def test_invalid_token(self, client: AsyncClient):
        r = await client.post(
            "/api/auth/reset-password",
            json={"token": "bad", "new_password": "NewPass123"},
        )
        assert r.status_code == 400

    async def test_wrong_token_type(self, client: AsyncClient):
        from app.services.auth import create_verification_token

        token = create_verification_token("user@example.com")
        r = await client.post(
            "/api/auth/reset-password",
            json={"token": token, "new_password": "NewPass123"},
        )
        assert r.status_code == 400
