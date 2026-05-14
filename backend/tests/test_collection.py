from unittest.mock import patch

from sqlalchemy import select

from app.models.user import User


async def _register_login(
    client, db_session, email="u@test.com", username="testuser", password="Passw0rd!"
):
    with patch("app.services.email.send_verification_email"):
        await client.post(
            "/api/auth/register",
            json={"email": email, "username": username, "password": password},
        )
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_verified = True
    await db_session.commit()
    r = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestMyCollection:
    async def test_empty_collection(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.get("/api/users/me/collection", headers=_auth(token))
        assert r.status_code == 200
        assert r.json() == []

    async def test_add_manual_game(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.post(
            "/api/users/me/collection",
            json={"game_title": "Ticket to Ride"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["game_title"] == "Ticket to Ride"
        assert data["source"] == "manual"
        assert data["status"] == "own"

        r2 = await client.get("/api/users/me/collection", headers=_auth(token))
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        assert r2.json()[0]["game_title"] == "Ticket to Ride"

    async def test_add_bgg_game(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.post(
            "/api/users/me/collection",
            json={"game_title": "Catan", "bgg_game_id": 13},
            headers=_auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["bgg_game_id"] == 13
        assert data["game_title"] == "Catan"

    async def test_duplicate_bgg_game_rejected(self, client, db_session):
        token = await _register_login(client, db_session)
        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Catan", "bgg_game_id": 13},
            headers=_auth(token),
        )
        r = await client.post(
            "/api/users/me/collection",
            json={"game_title": "Catan again", "bgg_game_id": 13},
            headers=_auth(token),
        )
        assert r.status_code == 409

    async def test_update_entry_status(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/users/me/collection",
                json={"game_title": "Catan"},
                headers=_auth(token),
            )
        ).json()
        r = await client.patch(
            f"/api/users/me/collection/{created['id']}",
            json={"status": "wishlist"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "wishlist"

    async def test_update_entry_notes(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/users/me/collection",
                json={"game_title": "Catan"},
                headers=_auth(token),
            )
        ).json()
        r = await client.patch(
            f"/api/users/me/collection/{created['id']}",
            json={"notes": "Great game!"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["notes"] == "Great game!"

    async def test_delete_entry(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/users/me/collection",
                json={"game_title": "Catan"},
                headers=_auth(token),
            )
        ).json()
        r = await client.delete(
            f"/api/users/me/collection/{created['id']}",
            headers=_auth(token),
        )
        assert r.status_code == 204

        r2 = await client.get("/api/users/me/collection", headers=_auth(token))
        assert r2.json() == []

    async def test_filter_by_status(self, client, db_session):
        token = await _register_login(client, db_session)
        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Catan", "status": "own"},
            headers=_auth(token),
        )
        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Pandemic", "status": "wishlist"},
            headers=_auth(token),
        )

        r = await client.get(
            "/api/users/me/collection?status=own", headers=_auth(token)
        )
        assert r.status_code == 200
        results = r.json()
        assert len(results) == 1
        assert results[0]["game_title"] == "Catan"

    async def test_requires_auth(self, client, db_session):
        r = await client.get("/api/users/me/collection")
        assert r.status_code in (401, 403)


class TestCollectionVisibility:
    async def test_public_game_visible_to_anyone(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        # Get user A's ID
        result = await db_session.execute(select(User).where(User.email == "a@t.com"))
        user_a = result.scalar_one()

        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Public Game", "collection_visible_to": "public"},
            headers=_auth(token_a),
        )

        r = await client.get(
            f"/api/users/{user_a.id}/collection", headers=_auth(token_b)
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["game_title"] == "Public Game"

    async def test_friends_game_visible_to_friend(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        result_a = await db_session.execute(select(User).where(User.email == "a@t.com"))
        user_a = result_a.scalar_one()

        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Friends Game", "collection_visible_to": "friends"},
            headers=_auth(token_a),
        )

        # Befriend: B sends request to A, A accepts
        req_r = await client.post(
            "/api/friends/request",
            json={"username": "usera"},
            headers=_auth(token_b),
        )
        assert req_r.status_code == 201
        friendship_id = req_r.json()["friendship_id"]

        accept_r = await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_a),
        )
        assert accept_r.status_code == 200

        r = await client.get(
            f"/api/users/{user_a.id}/collection", headers=_auth(token_b)
        )
        assert r.status_code == 200
        assert any(e["game_title"] == "Friends Game" for e in r.json())

    async def test_friends_game_not_visible_to_stranger(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        result_a = await db_session.execute(select(User).where(User.email == "a@t.com"))
        user_a = result_a.scalar_one()

        await client.post(
            "/api/users/me/collection",
            json={
                "game_title": "Friends Only Game",
                "collection_visible_to": "friends",
            },
            headers=_auth(token_a),
        )

        r = await client.get(
            f"/api/users/{user_a.id}/collection", headers=_auth(token_b)
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_private_game_not_visible_to_anyone(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        result_a = await db_session.execute(select(User).where(User.email == "a@t.com"))
        user_a = result_a.scalar_one()

        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Secret Game", "collection_visible_to": "private"},
            headers=_auth(token_a),
        )

        r = await client.get(
            f"/api/users/{user_a.id}/collection", headers=_auth(token_b)
        )
        assert r.status_code == 200
        assert r.json() == []

    async def test_owner_sees_all(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")

        result_a = await db_session.execute(select(User).where(User.email == "a@t.com"))
        user_a = result_a.scalar_one()

        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Public Game", "collection_visible_to": "public"},
            headers=_auth(token_a),
        )
        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Friends Game", "collection_visible_to": "friends"},
            headers=_auth(token_a),
        )
        await client.post(
            "/api/users/me/collection",
            json={"game_title": "Private Game", "collection_visible_to": "private"},
            headers=_auth(token_a),
        )

        r = await client.get(
            f"/api/users/{user_a.id}/collection", headers=_auth(token_a)
        )
        assert r.status_code == 200
        assert len(r.json()) == 3
