from datetime import date, timedelta
from unittest.mock import patch

from httpx import AsyncClient
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


def auth(token):
    return {"Authorization": f"Bearer {token}"}


async def _setup(client, db_session):
    """Create user, group, series and return token + ids."""
    token = await _register_login(client, db_session)
    gr = await client.post(
        "/api/groups", json={"name": "Test Group"}, headers=auth(token)
    )
    group_id = gr.json()["id"]
    sr = await client.post(
        f"/api/groups/{group_id}/series",
        json={
            "title": "Saturday Games",
            "recurrence": "weekly",
            "default_start_time": "19:00:00",
            "default_day_of_week": 5,
        },
        headers=auth(token),
    )
    series_id = sr.json()["id"]
    return token, group_id, series_id


OPTION = {
    "proposed_date": str(date.today() + timedelta(days=7)),
    "start_time": "19:00:00",
}


class TestCreatePoll:
    async def test_organiser_can_create_poll(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Pick a date"
        assert data["status"] == "open"
        assert len(data["options"]) == 1

    async def test_member_cannot_create_poll(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, group_id, series_id = await _setup(client, db_session)
            token2 = await _register_login(
                client, db_session, email="b@test.com", username="user2"
            )
            # join group
            inv = await client.post(
                f"/api/groups/{group_id}/invites",
                json={"expires_in_days": 7},
                headers=auth(token),
            )
            inv_token = inv.json()["token"]
            await client.post(f"/api/invites/{inv_token}/accept", headers=auth(token2))

            r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Unauthorised", "options": []},
                headers=auth(token2),
            )
        assert r.status_code == 403

    async def test_nonmember_cannot_create_poll(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            token2 = await _register_login(
                client, db_session, email="x@test.com", username="outsider"
            )
            r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Nope", "options": []},
                headers=auth(token2),
            )
        assert r.status_code == 403


class TestPollRespond:
    async def test_member_can_respond(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, group_id, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
        poll = poll_r.json()
        option_id = poll["options"][0]["id"]

        r = await client.post(
            f"/api/polls/{poll['id']}/respond",
            json={"responses": [{"option_id": option_id, "response": "yes"}]},
            headers=auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["my_responses"][option_id] == "yes"
        assert data["options"][0]["response_counts"]["yes"] == 1

    async def test_response_is_upserted(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
        poll = poll_r.json()
        option_id = poll["options"][0]["id"]

        await client.post(
            f"/api/polls/{poll['id']}/respond",
            json={"responses": [{"option_id": option_id, "response": "yes"}]},
            headers=auth(token),
        )
        # Change response
        r = await client.post(
            f"/api/polls/{poll['id']}/respond",
            json={"responses": [{"option_id": option_id, "response": "no"}]},
            headers=auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["my_responses"][option_id] == "no"
        assert data["options"][0]["response_counts"]["no"] == 1
        assert data["options"][0]["response_counts"]["yes"] == 0


class TestResolvePoll:
    async def test_resolve_creates_occurrence(self, client: AsyncClient, db_session):
        with (
            patch("app.api.polls.send_poll_created_email"),
            patch("app.api.polls.send_poll_resolved_email"),
        ):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()
            option_id = poll["options"][0]["id"]

            r = await client.post(
                f"/api/polls/{poll['id']}/resolve",
                json={"chosen_option_id": option_id},
                headers=auth(token),
            )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "resolved"
        assert data["chosen_option_id"] == option_id

        # Verify occurrence was created
        occs_r = await client.get(
            f"/api/series/{series_id}/occurrences", headers=auth(token)
        )
        occs = occs_r.json()
        assert any(o["occurrence_date"] == OPTION["proposed_date"] for o in occs)

    async def test_resolve_requires_organiser(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, group_id, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()
            option_id = poll["options"][0]["id"]

            token2 = await _register_login(
                client, db_session, email="b@test.com", username="user2"
            )
            inv = await client.post(
                f"/api/groups/{group_id}/invites",
                json={"expires_in_days": 7},
                headers=auth(token),
            )
            await client.post(
                f"/api/invites/{inv.json()['token']}/accept", headers=auth(token2)
            )

            r = await client.post(
                f"/api/polls/{poll['id']}/resolve",
                json={"chosen_option_id": option_id},
                headers=auth(token2),
            )
        assert r.status_code == 403


class TestGuestLink:
    async def test_create_poll_guest_link(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()

        r = await client.post(
            f"/api/polls/{poll['id']}/guest-link", headers=auth(token)
        )
        assert r.status_code == 201
        data = r.json()
        assert "token" in data
        assert "/poll-respond/" in data["url"]

    async def test_guest_can_resolve_token(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()

        link_r = await client.post(
            f"/api/polls/{poll['id']}/guest-link", headers=auth(token)
        )
        guest_token = link_r.json()["token"]

        r = await client.get(f"/api/guest/{guest_token}")
        assert r.status_code == 200
        data = r.json()
        assert data["type"] == "poll"
        assert data["poll_title"] == "Pick a date"

    async def test_guest_can_respond_to_poll(self, client: AsyncClient, db_session):
        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Pick a date", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()
            option_id = poll["options"][0]["id"]

        link_r = await client.post(
            f"/api/polls/{poll['id']}/guest-link", headers=auth(token)
        )
        guest_token = link_r.json()["token"]

        r = await client.post(
            f"/api/guest/{guest_token}/poll",
            json={
                "guest_name": "Guest Alice",
                "responses": [{"option_id": option_id, "response": "yes"}],
            },
        )
        assert r.status_code == 200

        # Response should appear in poll
        poll_r2 = await client.get(f"/api/polls/{poll['id']}", headers=auth(token))
        assert poll_r2.json()["options"][0]["response_counts"]["yes"] == 1

    async def test_expired_token_rejected(self, client: AsyncClient, db_session):
        from datetime import timedelta

        from sqlalchemy import select as sa_select

        from app.models.scheduler import GuestToken

        with patch("app.api.polls.send_poll_created_email"):
            token, _, series_id = await _setup(client, db_session)
            poll_r = await client.post(
                f"/api/series/{series_id}/polls",
                json={"title": "Expire test", "options": [OPTION]},
                headers=auth(token),
            )
            poll = poll_r.json()

        link_r = await client.post(
            f"/api/polls/{poll['id']}/guest-link", headers=auth(token)
        )
        guest_token_str = link_r.json()["token"]

        # Expire the token
        from datetime import datetime, timezone

        result = await db_session.execute(
            sa_select(GuestToken).where(GuestToken.token == guest_token_str)
        )
        gt = result.scalar_one()
        gt.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.commit()

        r = await client.get(f"/api/guest/{guest_token_str}")
        assert r.status_code == 410
