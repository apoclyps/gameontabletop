import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.user import User


async def _register_login(client, db_session, email="u@test.com", username="testuser", password="Passw0rd!"):
    with patch("app.services.email.send_verification_email"):
        await client.post("/api/auth/register", json={"email": email, "username": username, "password": password})
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_verified = True
    await db_session.commit()
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestFriendRequests:
    async def test_send_friend_request(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        await _register_login(client, db_session, "b@t.com", "userb")

        r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        assert r.status_code == 201
        data = r.json()
        assert "friendship_id" in data
        assert data["status"] == "pending"

    async def test_request_unknown_user(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")

        r = await client.post(
            "/api/friends/request",
            json={"username": "nobody"},
            headers=_auth(token_a),
        )
        assert r.status_code == 400

    async def test_cannot_friend_yourself(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")

        r = await client.post(
            "/api/friends/request",
            json={"username": "usera"},
            headers=_auth(token_a),
        )
        assert r.status_code == 400

    async def test_duplicate_request_rejected(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        await _register_login(client, db_session, "b@t.com", "userb")

        await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        assert r.status_code in (400, 409)

    async def test_accept_request(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]

        r = await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_b),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    async def test_decline_request(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]

        r = await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "declined"},
            headers=_auth(token_b),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "declined"

    async def test_accepted_friendship_is_bidirectional(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]
        await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_b),
        )

        # Both users should see each other in their friends list
        r_a = await client.get("/api/friends", headers=_auth(token_a))
        assert r_a.status_code == 200
        assert any(f["username"] == "userb" for f in r_a.json())

        r_b = await client.get("/api/friends", headers=_auth(token_b))
        assert r_b.status_code == 200
        assert any(f["username"] == "usera" for f in r_b.json())


class TestFriendsCollection:
    async def test_friends_aggregate_collection(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        # B adds a BGG game with status=own, public visibility
        await client.post(
            "/api/users/me/collection",
            json={
                "game_title": "Catan",
                "bgg_game_id": 13,
                "status": "own",
                "collection_visible_to": "public",
            },
            headers=_auth(token_b),
        )

        # A and B become friends
        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]
        await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_b),
        )

        # A's friends collection should include B's game
        r = await client.get("/api/friends/collection", headers=_auth(token_a))
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["bgg_game_id"] == 13
        assert data[0]["game_title"] == "Catan"
        assert len(data[0]["owners"]) == 1
        assert data[0]["owners"][0]["username"] == "userb"

    async def test_strangers_games_not_included(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")
        token_c = await _register_login(client, db_session, "c@t.com", "userc")

        # A and B become friends
        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]
        await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_b),
        )

        # C (not A's friend) adds a game
        await client.post(
            "/api/users/me/collection",
            json={
                "game_title": "Secret Game",
                "bgg_game_id": 999,
                "status": "own",
                "collection_visible_to": "public",
            },
            headers=_auth(token_c),
        )

        # A's friends collection should NOT include C's game
        r = await client.get("/api/friends/collection", headers=_auth(token_a))
        assert r.status_code == 200
        assert not any(e["bgg_game_id"] == 999 for e in r.json())


class TestBlock:
    async def test_block_prevents_new_request(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        # A sends request to B
        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]

        # B blocks A
        await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "blocked"},
            headers=_auth(token_b),
        )

        # A tries to send another request to B -> should be blocked
        r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        assert r.status_code == 400

    async def test_delete_friendship(self, client, db_session):
        token_a = await _register_login(client, db_session, "a@t.com", "usera")
        token_b = await _register_login(client, db_session, "b@t.com", "userb")

        req_r = await client.post(
            "/api/friends/request",
            json={"username": "userb"},
            headers=_auth(token_a),
        )
        friendship_id = req_r.json()["friendship_id"]
        await client.patch(
            f"/api/friends/{friendship_id}",
            json={"status": "accepted"},
            headers=_auth(token_b),
        )

        # Delete friendship
        r = await client.delete(f"/api/friends/{friendship_id}", headers=_auth(token_a))
        assert r.status_code == 204

        # No longer in friends list
        r2 = await client.get("/api/friends", headers=_auth(token_a))
        assert r2.status_code == 200
        assert r2.json() == []
