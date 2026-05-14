import uuid
from datetime import date, timedelta
from unittest.mock import patch

from sqlalchemy import select

from app.models.scheduler import NightOccurrence
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


async def _create_group(client, token, name="Games"):
    r = await client.post("/api/groups", json={"name": name}, headers=_auth(token))
    return r.json()


class TestCreateSeries:
    async def test_creates_once_off_series(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today() + timedelta(days=7))

        r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "One-off Night",
                "recurrence": "once",
                "series_start_date": start,
                "default_start_time": "19:00:00",
            },
            headers=_auth(token),
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "One-off Night"
        assert data["recurrence"] == "once"
        assert data["status"] == "active"

    async def test_once_off_auto_generates_one_occurrence(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today() + timedelta(days=7))

        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "One Night",
                "recurrence": "once",
                "series_start_date": start,
            },
            headers=_auth(token),
        )
        series_id = series_r.json()["id"]

        sid = uuid.UUID(series_id)
        result = await db_session.execute(
            select(NightOccurrence).where(NightOccurrence.series_id == sid)
        )
        occurrences = result.scalars().all()
        assert len(occurrences) == 1
        assert str(occurrences[0].occurrence_date) == start

    async def test_creates_weekly_series(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today())

        r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "Weekly Games",
                "recurrence": "weekly",
                "series_start_date": start,
                "default_start_time": "19:00:00",
                "default_day_of_week": 5,
            },
            headers=_auth(token),
        )
        assert r.status_code == 201

    async def test_weekly_generates_multiple_occurrences(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today())

        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "Weekly",
                "recurrence": "weekly",
                "series_start_date": start,
            },
            headers=_auth(token),
        )
        series_id = series_r.json()["id"]

        sid = uuid.UUID(series_id)
        result = await db_session.execute(
            select(NightOccurrence).where(NightOccurrence.series_id == sid)
        )
        occurrences = result.scalars().all()
        assert len(occurrences) >= 8

    async def test_member_cannot_create_series(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        group = await _create_group(client, token1)
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

        r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Games", "recurrence": "once"},
            headers=_auth(token2),
        )
        assert r.status_code == 403


class TestGetSeries:
    async def test_get_series_triggers_generation(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today())
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "Biweekly",
                "recurrence": "biweekly",
                "series_start_date": start,
            },
            headers=_auth(token),
        )
        series_id = series_r.json()["id"]

        r = await client.get(f"/api/series/{series_id}", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["title"] == "Biweekly"

    async def test_non_member_cannot_get_series(self, client, db_session):
        token1 = await _register_login(client, db_session, "a@t.com", "user1")
        token2 = await _register_login(client, db_session, "b@t.com", "user2")
        group = await _create_group(client, token1)
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Games", "recurrence": "once"},
            headers=_auth(token1),
        )
        r = await client.get(
            f"/api/series/{series_r.json()['id']}", headers=_auth(token2)
        )
        assert r.status_code == 403


class TestUpdateSeries:
    async def test_put_on_hold(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={
                "title": "Games",
                "recurrence": "weekly",
                "series_start_date": str(date.today()),
            },
            headers=_auth(token),
        )
        series_id = series_r.json()["id"]

        r = await client.patch(
            f"/api/series/{series_id}", json={"status": "on_hold"}, headers=_auth(token)
        )
        assert r.status_code == 200
        assert r.json()["status"] == "on_hold"

    async def test_cancel_series(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Games", "recurrence": "once"},
            headers=_auth(token),
        )
        r = await client.patch(
            f"/api/series/{series_r.json()['id']}",
            json={"status": "cancelled"},
            headers=_auth(token),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"

    async def test_update_title(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Old Title", "recurrence": "once"},
            headers=_auth(token),
        )
        r = await client.patch(
            f"/api/series/{series_r.json()['id']}",
            json={"title": "New Title"},
            headers=_auth(token),
        )
        assert r.json()["title"] == "New Title"


class TestListOccurrences:
    async def test_lists_occurrences(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today())
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Games", "recurrence": "weekly", "series_start_date": start},
            headers=_auth(token),
        )
        r = await client.get(
            f"/api/series/{series_r.json()['id']}/occurrences", headers=_auth(token)
        )
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_occurrences_sorted_by_date(self, client, db_session):
        token = await _register_login(client, db_session)
        group = await _create_group(client, token)
        start = str(date.today())
        series_r = await client.post(
            f"/api/groups/{group['id']}/series",
            json={"title": "Games", "recurrence": "weekly", "series_start_date": start},
            headers=_auth(token),
        )
        r = await client.get(
            f"/api/series/{series_r.json()['id']}/occurrences", headers=_auth(token)
        )
        dates = [o["occurrence_date"] for o in r.json()]
        assert dates == sorted(dates)
