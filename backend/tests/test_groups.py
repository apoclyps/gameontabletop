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


class TestCreateGroup:
    async def test_creates_group(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.post(
            "/api/groups", json={"name": "Saturday Games"}, headers=_auth(token)
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Saturday Games"
        assert data["slug"] == "saturday-games"
        assert data["my_role"] == "organiser"
        assert data["member_count"] == 1

    async def test_auto_slugifies(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.post(
            "/api/groups", json={"name": "My Board Game Club!"}, headers=_auth(token)
        )
        assert r.status_code == 201
        assert r.json()["slug"] == "my-board-game-club"

    async def test_custom_slug(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.post(
            "/api/groups",
            json={"name": "Games", "slug": "custom-slug"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        assert r.json()["slug"] == "custom-slug"

    async def test_requires_auth(self, client, db_session):
        r = await client.post("/api/groups", json={"name": "Games"})
        assert r.status_code in (401, 403)


class TestListGroups:
    async def test_lists_own_groups(self, client, db_session):
        token = await _register_login(client, db_session)
        await client.post("/api/groups", json={"name": "Group A"}, headers=_auth(token))
        await client.post("/api/groups", json={"name": "Group B"}, headers=_auth(token))
        r = await client.get("/api/groups", headers=_auth(token))
        assert r.status_code == 200
        assert len(r.json()) == 2

    async def test_does_not_list_other_users_groups(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        await client.post(
            "/api/groups", json={"name": "User1 Group"}, headers=_auth(token1)
        )
        r = await client.get("/api/groups", headers=_auth(token2))
        assert r.json() == []


class TestGetGroup:
    async def test_member_can_get_group(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token)
            )
        ).json()
        r = await client.get(f"/api/groups/{created['id']}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["name"] == "Games"

    async def test_non_member_gets_403(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        r = await client.get(f"/api/groups/{created['id']}", headers=_auth(token2))
        assert r.status_code == 403

    async def test_nonexistent_group_404(self, client, db_session):
        token = await _register_login(client, db_session)
        r = await client.get(
            "/api/groups/00000000-0000-0000-0000-000000000000", headers=_auth(token)
        )
        assert r.status_code == 404


class TestUpdateGroup:
    async def test_organiser_can_update(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token)
            )
        ).json()
        r = await client.patch(
            f"/api/groups/{created['id']}",
            json={"name": "Updated Games"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Games"

    async def test_member_cannot_update(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()

        invite = (
            await client.post(
                f"/api/groups/{created['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )

        r = await client.patch(
            f"/api/groups/{created['id']}",
            json={"name": "Hacked"},
            headers=_auth(token2),
        )
        assert r.status_code == 403


class TestDeleteGroup:
    async def test_owner_can_delete(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token)
            )
        ).json()
        r = await client.delete(f"/api/groups/{created['id']}", headers=_auth(token))
        assert r.status_code == 204

    async def test_non_owner_cannot_delete(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        invite = (
            await client.post(
                f"/api/groups/{created['id']}/invites",
                json={"role": "organiser", "expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )
        r = await client.delete(f"/api/groups/{created['id']}", headers=_auth(token2))
        assert r.status_code == 403


class TestMembers:
    async def test_list_members(self, client, db_session):
        token = await _register_login(client, db_session)
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token)
            )
        ).json()
        r = await client.get(
            f"/api/groups/{created['id']}/members", headers=_auth(token)
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["role"] == "organiser"

    async def test_remove_member(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        invite = (
            await client.post(
                f"/api/groups/{created['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        accept_r = await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )
        user2_id = accept_r.json()

        members_r = await client.get(
            f"/api/groups/{created['id']}/members", headers=_auth(token1)
        )
        user2_member = next(m for m in members_r.json() if m["role"] == "member")
        user2_id = user2_member["user_id"]

        r = await client.delete(
            f"/api/groups/{created['id']}/members/{user2_id}", headers=_auth(token1)
        )
        assert r.status_code == 204


class TestInvites:
    async def test_create_and_accept_invite(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()

        with patch("app.api.groups.send_group_invite_email"):
            invite_r = await client.post(
                f"/api/groups/{created['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        assert invite_r.status_code == 201
        token = invite_r.json()["token"]

        preview = await client.get(f"/api/invites/{token}")
        assert preview.status_code == 200
        assert preview.json()["group_name"] == "Games"

        accept = await client.post(
            f"/api/invites/{token}/accept", headers=_auth(token2)
        )
        assert accept.status_code == 200

        members = await client.get(
            f"/api/groups/{created['id']}/members", headers=_auth(token1)
        )
        assert len(members.json()) == 2

    async def test_expired_invite_404(self, client, db_session):
        r = await client.get("/api/invites/nonexistent-token")
        assert r.status_code == 404

    async def test_accept_twice_is_idempotent(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        created = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        invite = (
            await client.post(
                f"/api/groups/{created['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )
        r = await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )
        assert r.status_code == 200
        assert "Already a member" in r.json()["message"]
