from datetime import date, timedelta
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


async def _setup(client, db_session, email="u@test.com", username="testuser"):
    token = await _register_login(client, db_session, email, username)
    group = (
        await client.post("/api/groups", json={"name": "Games"}, headers=_auth(token))
    ).json()
    start = str(date.today() + timedelta(days=7))
    series = (
        await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "Board Night",
                "recurrence": "once",
                "series_start_date": start,
            },
            headers=_auth(token),
        )
    ).json()
    occs = (
        await client.get(
            f"/api/series/{series['id']}/occurrences", headers=_auth(token)
        )
    ).json()
    return token, group, series, occs[0]


class TestGetOccurrence:
    async def test_get_occurrence(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        r = await client.get(f"/api/occurrences/{occ['id']}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["status"] == "scheduled"
        assert r.json()["rsvp_counts"] == {"yes": 0, "no": 0, "maybe": 0}

    async def test_non_member_gets_403(self, client, db_session):
        _, _, _, occ = await _setup(client, db_session)
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        r = await client.get(f"/api/occurrences/{occ['id']}", headers=_auth(token2))
        assert r.status_code == 403


class TestCreateManualOccurrence:
    async def test_organiser_can_create(self, client, db_session):
        token, _, series, _ = await _setup(client, db_session)
        future = str(date.today() + timedelta(days=30))
        r = await client.post(
            f"/api/series/{series['id']}/occurrences",
            json={"occurrence_date": future, "start_time": "20:00:00"},
            headers=_auth(token),
        )
        assert r.status_code == 201
        assert r.json()["is_auto_generated"] is False

    async def test_member_cannot_create(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        group = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        invite = (
            await client.post(
                f"/api/groups/{group['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )
        series = (
            await client.post(
                f"/api/groups/{group['id']}/series",
                json={"title": "Games", "recurrence": "once"},
                headers=_auth(token1),
            )
        ).json()
        r = await client.post(
            f"/api/series/{series['id']}/occurrences",
            json={
                "occurrence_date": str(date.today() + timedelta(days=14)),
                "start_time": "19:00:00",
            },
            headers=_auth(token2),
        )
        assert r.status_code == 403


class TestUpdateOccurrence:
    async def test_postpone_occurrence(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        new_date = str(date.today() + timedelta(days=14))
        r = await client.patch(
            f"/api/occurrences/{occ['id']}",
            json={"status": "postponed", "occurrence_date": new_date},
            headers=_auth(token),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "postponed"
        assert data["occurrence_date"] == new_date
        assert data["postponed_from_date"] is not None

    async def test_cancel_occurrence(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        r = await client.patch(
            f"/api/occurrences/{occ['id']}",
            json={"status": "cancelled"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    async def test_update_notes(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        r = await client.patch(
            f"/api/occurrences/{occ['id']}",
            json={"notes": "Bring snacks!"},
            headers=_auth(token),
        )
        assert r.json()["notes"] == "Bring snacks!"


class TestRsvp:
    async def test_rsvp_yes(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        r = await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "yes"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["response"] == "yes"

    async def test_rsvp_with_note(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        r = await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "maybe", "note": "Might be late"},
            headers=_auth(token),
        )
        assert r.json()["note"] == "Might be late"

    async def test_rsvp_updates_existing(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "yes"},
            headers=_auth(token),
        )
        r = await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "no"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["response"] == "no"

    async def test_rsvp_counts_update(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        group = (
            await client.post(
                "/api/groups", json={"name": "Games"}, headers=_auth(token1)
            )
        ).json()
        invite = (
            await client.post(
                f"/api/groups/{group['id']}/invites",
                json={"expires_in_days": 7},
                headers=_auth(token1),
            )
        ).json()
        await client.post(
            f"/api/invites/{invite['token']}/accept", headers=_auth(token2)
        )

        start = str(date.today() + timedelta(days=7))
        series = (
            await client.post(
                f"/api/groups/{group['id']}/series",
                json={
                    "title": "Night",
                    "recurrence": "once",
                    "series_start_date": start,
                },
                headers=_auth(token1),
            )
        ).json()
        occs = (
            await client.get(
                f"/api/series/{series['id']}/occurrences", headers=_auth(token1)
            )
        ).json()
        occ_id = occs[0]["id"]

        await client.post(
            f"/api/occurrences/{occ_id}/rsvp",
            json={"response": "yes"},
            headers=_auth(token1),
        )
        await client.post(
            f"/api/occurrences/{occ_id}/rsvp",
            json={"response": "maybe"},
            headers=_auth(token2),
        )

        r = await client.get(f"/api/occurrences/{occ_id}", headers=_auth(token1))
        counts = r.json()["rsvp_counts"]
        assert counts["yes"] == 1
        assert counts["maybe"] == 1
        assert counts["no"] == 0

    async def test_cannot_rsvp_cancelled_occurrence(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        await client.patch(
            f"/api/occurrences/{occ['id']}",
            json={"status": "cancelled"},
            headers=_auth(token),
        )
        r = await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "yes"},
            headers=_auth(token),
        )
        assert r.status_code == 400

    async def test_list_rsvps(self, client, db_session):
        token, _, _, occ = await _setup(client, db_session)
        await client.post(
            f"/api/occurrences/{occ['id']}/rsvp",
            json={"response": "yes"},
            headers=_auth(token),
        )
        r = await client.get(
            f"/api/occurrences/{occ['id']}/rsvps", headers=_auth(token)
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["response"] == "yes"
