#!/usr/bin/env python3
"""
Idempotent database seeder for Game On Tabletop.

Populates the database with example users, friendships, groups,
locations, series, game nights, RSVPs, and game collections.
Safe to run repeatedly — existing records are skipped.

Usage:
    uv run python seed.py
    DATABASE_URL=postgresql+asyncpg://... uv run python seed.py

Seed accounts (password: Seed@1234!):
    alice@example.com   @alice   organiser, The Tabletop Collective
    bob@example.com     @bob     organiser, Board Game Basement
    carol@example.com   @carol
    dave@example.com    @dave
    eve@example.com     @eve
"""

import asyncio
import os
import sys
from datetime import UTC, date, datetime, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models.collection import UserFriendship, UserGameCollection
from app.models.group import Group, GroupMember
from app.models.location import Location
from app.models.scheduler import NightOccurrence, NightSeries, Rsvp
from app.models.user import User
from app.services.auth import hash_password

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/app",
)

SEED_PASSWORD = "Seed@1234!"

# ─── Seed data ────────────────────────────────────────────────────────────────

USERS = [
    {
        "email": "alice@example.com",
        "username": "alice",
        "display_name": "Alice Chen",
        "bio": "Board game enthusiast and frequent organiser.",
        "profile_public": True,
        "stats_public": True,
    },
    {
        "email": "bob@example.com",
        "username": "bob",
        "display_name": "Bob Kowalski",
        "bio": "Strategy games are my passion.",
        "profile_public": True,
        "stats_public": True,
    },
    {
        "email": "carol@example.com",
        "username": "carol",
        "display_name": "Carol Smith",
        "bio": "I love cooperative games!",
        "profile_public": True,
        "stats_public": True,
    },
    {
        "email": "dave@example.com",
        "username": "dave",
        "display_name": "Dave Nguyen",
        "bio": "Worker placement and deck-building. Always.",
        "profile_public": False,
        "stats_public": False,
    },
    {
        "email": "eve@example.com",
        "username": "eve",
        "display_name": "Eve Martinez",
        "bio": "Newcomer to the hobby — loving every game!",
        "profile_public": True,
        "stats_public": True,
    },
]

# (requester_username, addressee_username, status)
FRIENDSHIPS = [
    ("alice", "bob", "accepted"),
    ("alice", "carol", "accepted"),
    ("bob", "dave", "accepted"),
    ("carol", "eve", "accepted"),
    ("alice", "dave", "pending"),
]

GAMES = {
    "alice": [
        {
            "title": "Ticket to Ride",
            "bgg_id": 9209,
            "min": 2,
            "max": 5,
            "complexity": 1.86,
        },
        {"title": "Wingspan", "bgg_id": 266192, "min": 1, "max": 5, "complexity": 2.45},
        {"title": "Pandemic", "bgg_id": 30549, "min": 2, "max": 4, "complexity": 2.41},
        {"title": "7 Wonders", "bgg_id": 68448, "min": 2, "max": 7, "complexity": 2.33},
    ],
    "bob": [
        {
            "title": "Terraforming Mars",
            "bgg_id": 167791,
            "min": 1,
            "max": 5,
            "complexity": 3.25,
        },
        {
            "title": "Gloomhaven",
            "bgg_id": 174430,
            "min": 1,
            "max": 4,
            "complexity": 3.86,
        },
        {"title": "Scythe", "bgg_id": 169786, "min": 1, "max": 5, "complexity": 3.44},
        {
            "title": "Brass: Birmingham",
            "bgg_id": 224517,
            "min": 2,
            "max": 4,
            "complexity": 3.91,
        },
    ],
    "carol": [
        {"title": "Catan", "bgg_id": 13, "min": 3, "max": 4, "complexity": 2.32},
        {
            "title": "Codenames",
            "bgg_id": 178900,
            "min": 2,
            "max": 8,
            "complexity": 1.26,
        },
        {"title": "Pandemic", "bgg_id": 30549, "min": 2, "max": 4, "complexity": 2.41},
    ],
    "dave": [
        {"title": "Dominion", "bgg_id": 36218, "min": 2, "max": 4, "complexity": 2.33},
        {"title": "Agricola", "bgg_id": 31260, "min": 1, "max": 5, "complexity": 3.64},
        {"title": "Scythe", "bgg_id": 169786, "min": 1, "max": 5, "complexity": 3.44},
    ],
    "eve": [
        {
            "title": "Sushi Go Party!",
            "bgg_id": 192291,
            "min": 2,
            "max": 8,
            "complexity": 1.12,
        },
        {"title": "Azul", "bgg_id": 230802, "min": 2, "max": 4, "complexity": 1.77},
        {"title": "Catan", "bgg_id": 13, "min": 3, "max": 4, "complexity": 2.32},
    ],
}

# Groups contain their locations, series, occurrences, and RSVPs inline
# so all related data stays together and is easy to extend.
GROUPS = [
    {
        "slug": "tabletop-collective",
        "name": "The Tabletop Collective",
        "description": "A friendly group that meets weekly for all kinds of board games.",
        "is_public": True,
        "owner": "alice",
        "members": [
            ("alice", "organiser"),
            ("bob", "member"),
            ("carol", "member"),
            ("dave", "member"),
        ],
        "locations": [
            {
                "name": "Alice's Place",
                "address": "42 Board Game Lane, London",
                "is_virtual": False,
            },
            {
                "name": "Online",
                "is_virtual": True,
                "virtual_url": "https://meet.google.com/abc-defg-hij",
            },
        ],
        "series": [
            {
                "title": "Friday Night Games",
                "description": "Weekly Friday session — all games welcome.",
                "recurrence": "weekly",
                "default_day_of_week": 4,
                "default_start_time": time(19, 0),
                "default_duration_minutes": 180,
                "location_name": "Alice's Place",
                "created_by": "alice",
                "occurrences": [
                    {
                        "date": date(2026, 4, 17),
                        "status": "completed",
                        "notes": "Played Wingspan — Alice won!",
                    },
                    {
                        "date": date(2026, 4, 24),
                        "status": "completed",
                        "notes": "Terraforming Mars marathon.",
                    },
                    {
                        "date": date(2026, 5, 1),
                        "status": "completed",
                        "notes": "Short games night — Codenames and Azul.",
                    },
                    {"date": date(2026, 5, 15), "status": "scheduled", "notes": None},
                    {"date": date(2026, 5, 22), "status": "scheduled", "notes": None},
                    {"date": date(2026, 6, 5), "status": "scheduled", "notes": None},
                ],
                "rsvps": {
                    date(2026, 4, 17): [
                        ("alice", "yes"),
                        ("bob", "yes"),
                        ("carol", "yes"),
                        ("dave", "no"),
                    ],
                    date(2026, 4, 24): [
                        ("alice", "yes"),
                        ("bob", "yes"),
                        ("carol", "maybe"),
                        ("dave", "yes"),
                    ],
                    date(2026, 5, 1): [
                        ("alice", "yes"),
                        ("bob", "no"),
                        ("carol", "yes"),
                    ],
                    date(2026, 5, 15): [("alice", "yes"), ("bob", "yes")],
                    date(2026, 5, 22): [("alice", "yes")],
                },
            },
            {
                "title": "Monthly Megagame",
                "description": "Long-form games on the first Saturday of each month.",
                "recurrence": "monthly",
                "default_day_of_week": 5,
                "default_start_time": time(14, 0),
                "default_duration_minutes": 360,
                "location_name": "Online",
                "created_by": "alice",
                "occurrences": [
                    {
                        "date": date(2026, 3, 7),
                        "status": "completed",
                        "notes": "Gloomhaven scenario 5 — victory!",
                    },
                    {
                        "date": date(2026, 4, 4),
                        "status": "completed",
                        "notes": "Scythe with all factions.",
                    },
                    {
                        "date": date(2026, 5, 2),
                        "status": "completed",
                        "notes": "Agricola full game.",
                    },
                    {"date": date(2026, 6, 6), "status": "scheduled", "notes": None},
                    {"date": date(2026, 7, 4), "status": "scheduled", "notes": None},
                ],
                "rsvps": {
                    date(2026, 3, 7): [
                        ("alice", "yes"),
                        ("bob", "yes"),
                        ("carol", "yes"),
                        ("dave", "yes"),
                    ],
                    date(2026, 4, 4): [
                        ("alice", "yes"),
                        ("bob", "yes"),
                        ("carol", "no"),
                        ("dave", "yes"),
                    ],
                    date(2026, 6, 6): [("alice", "yes"), ("carol", "yes")],
                },
            },
        ],
    },
    {
        "slug": "board-game-basement",
        "name": "Board Game Basement",
        "description": "Bob's private gaming den. Heavy games only.",
        "is_public": False,
        "owner": "bob",
        "members": [
            ("bob", "organiser"),
            ("dave", "member"),
            ("eve", "member"),
        ],
        "locations": [
            {
                "name": "Bob's Basement",
                "address": "7 Strategy Street, Manchester",
                "is_virtual": False,
            },
        ],
        "series": [
            {
                "title": "Heavy Game Sunday",
                "description": "Complex strategy games every other Sunday.",
                "recurrence": "biweekly",
                "default_day_of_week": 6,
                "default_start_time": time(13, 0),
                "default_duration_minutes": 300,
                "location_name": "Bob's Basement",
                "created_by": "bob",
                "occurrences": [
                    {
                        "date": date(2026, 4, 26),
                        "status": "completed",
                        "notes": "Brass: Birmingham. Dave won.",
                    },
                    {
                        "date": date(2026, 5, 10),
                        "status": "completed",
                        "notes": "Spirit Island on hard difficulty.",
                    },
                    {"date": date(2026, 5, 24), "status": "scheduled", "notes": None},
                    {"date": date(2026, 6, 7), "status": "scheduled", "notes": None},
                ],
                "rsvps": {
                    date(2026, 4, 26): [
                        ("bob", "yes"),
                        ("dave", "yes"),
                        ("eve", "yes"),
                    ],
                    date(2026, 5, 10): [
                        ("bob", "yes"),
                        ("dave", "yes"),
                        ("eve", "maybe"),
                    ],
                    date(2026, 5, 24): [("bob", "yes"), ("dave", "yes")],
                },
            },
        ],
    },
]

# ─── Seeder functions ─────────────────────────────────────────────────────────


async def _seed_users(session: AsyncSession, hashed_pw: str) -> dict[str, User]:
    users: dict[str, User] = {}
    for data in USERS:
        result = await session.execute(select(User).where(User.email == data["email"]))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                email=data["email"],
                username=data["username"],
                display_name=data["display_name"],
                bio=data["bio"],
                hashed_password=hashed_pw,
                is_active=True,
                is_verified=True,
                profile_public=data["profile_public"],
                stats_public=data["stats_public"],
            )
            session.add(user)
            await session.flush()
            print(f"  + {data['username']}")
        else:
            print(f"  ~ {data['username']} (exists)")
        users[data["username"]] = user
    return users


async def _seed_friendships(session: AsyncSession, users: dict[str, User]) -> None:
    for req_name, addr_name, status in FRIENDSHIPS:
        req_id = users[req_name].id
        addr_id = users[addr_name].id
        result = await session.execute(
            select(UserFriendship).where(
                or_(
                    and_(
                        UserFriendship.requester_id == req_id,
                        UserFriendship.addressee_id == addr_id,
                    ),
                    and_(
                        UserFriendship.requester_id == addr_id,
                        UserFriendship.addressee_id == req_id,
                    ),
                )
            )
        )
        if result.scalar_one_or_none() is None:
            session.add(
                UserFriendship(
                    requester_id=req_id,
                    addressee_id=addr_id,
                    status=status,
                    responded_at=datetime.now(UTC) if status == "accepted" else None,
                )
            )
            print(f"  + {req_name} <-> {addr_name} ({status})")
        else:
            print(f"  ~ {req_name} <-> {addr_name} (exists)")


async def _seed_games(session: AsyncSession, users: dict[str, User]) -> None:
    for username, games in GAMES.items():
        user = users[username]
        for game in games:
            result = await session.execute(
                select(UserGameCollection).where(
                    and_(
                        UserGameCollection.user_id == user.id,
                        UserGameCollection.bgg_game_id == game["bgg_id"],
                    )
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    UserGameCollection(
                        user_id=user.id,
                        bgg_game_id=game["bgg_id"],
                        game_title=game["title"],
                        min_players=game["min"],
                        max_players=game["max"],
                        complexity=game["complexity"],
                        status="own",
                        source="manual",
                        collection_visible_to="friends",
                    )
                )
                print(f"  + {game['title']} -> @{username}")
            else:
                print(f"  ~ {game['title']} -> @{username} (exists)")


async def _seed_groups(session: AsyncSession, users: dict[str, User]) -> None:
    for group_data in GROUPS:
        # Group
        result = await session.execute(
            select(Group).where(Group.slug == group_data["slug"])
        )
        group = result.scalar_one_or_none()
        if group is None:
            group = Group(
                name=group_data["name"],
                description=group_data["description"],
                slug=group_data["slug"],
                owner_id=users[group_data["owner"]].id,
                is_public=group_data["is_public"],
            )
            session.add(group)
            await session.flush()
            print(f"  + group '{group_data['name']}'")
        else:
            print(f"  ~ group '{group_data['name']}' (exists)")

        # Members
        for username, role in group_data["members"]:
            member = await session.get(GroupMember, (group.id, users[username].id))
            if member is None:
                session.add(
                    GroupMember(
                        group_id=group.id, user_id=users[username].id, role=role
                    )
                )
                print(f"    + member @{username} ({role})")
            else:
                print(f"    ~ member @{username} (exists)")

        # Locations
        location_map: dict[str, Location] = {}
        for loc_data in group_data["locations"]:
            result = await session.execute(
                select(Location).where(
                    and_(
                        Location.group_id == group.id,
                        Location.name == loc_data["name"],
                    )
                )
            )
            loc = result.scalar_one_or_none()
            if loc is None:
                loc = Location(
                    group_id=group.id,
                    name=loc_data["name"],
                    address=loc_data.get("address"),
                    is_virtual=loc_data.get("is_virtual", False),
                    virtual_url=loc_data.get("virtual_url"),
                )
                session.add(loc)
                await session.flush()
                print(f"    + location '{loc_data['name']}'")
            else:
                print(f"    ~ location '{loc_data['name']}' (exists)")
            location_map[loc_data["name"]] = loc

        # Series
        for series_data in group_data["series"]:
            result = await session.execute(
                select(NightSeries).where(
                    and_(
                        NightSeries.group_id == group.id,
                        NightSeries.title == series_data["title"],
                    )
                )
            )
            series = result.scalar_one_or_none()
            default_loc = location_map.get(series_data["location_name"])
            if series is None:
                series = NightSeries(
                    group_id=group.id,
                    title=series_data["title"],
                    description=series_data["description"],
                    recurrence=series_data["recurrence"],
                    default_day_of_week=series_data["default_day_of_week"],
                    default_start_time=series_data["default_start_time"],
                    default_duration_minutes=series_data["default_duration_minutes"],
                    default_location_id=default_loc.id if default_loc else None,
                    created_by=users[series_data["created_by"]].id,
                    status="active",
                )
                session.add(series)
                await session.flush()
                print(f"    + series '{series_data['title']}'")
            else:
                print(f"    ~ series '{series_data['title']}' (exists)")

            # Occurrences + RSVPs
            rsvp_map = series_data.get("rsvps", {})
            for occ_data in series_data["occurrences"]:
                result = await session.execute(
                    select(NightOccurrence).where(
                        and_(
                            NightOccurrence.series_id == series.id,
                            NightOccurrence.occurrence_date == occ_data["date"],
                        )
                    )
                )
                occurrence = result.scalar_one_or_none()
                if occurrence is None:
                    occurrence = NightOccurrence(
                        series_id=series.id,
                        occurrence_date=occ_data["date"],
                        start_time=series_data["default_start_time"],
                        location_id=default_loc.id if default_loc else None,
                        status=occ_data["status"],
                        notes=occ_data["notes"],
                        is_auto_generated=False,
                    )
                    session.add(occurrence)
                    await session.flush()
                    status = occ_data["status"]
                    print(f"      + occurrence {occ_data['date']} ({status})")
                else:
                    print(f"      ~ occurrence {occ_data['date']} (exists)")

                for username, response in rsvp_map.get(occ_data["date"], []):
                    user = users[username]
                    result = await session.execute(
                        select(Rsvp).where(
                            and_(
                                Rsvp.occurrence_id == occurrence.id,
                                Rsvp.user_id == user.id,
                            )
                        )
                    )
                    if result.scalar_one_or_none() is None:
                        session.add(
                            Rsvp(
                                occurrence_id=occurrence.id,
                                user_id=user.id,
                                response=response,
                            )
                        )
                        print(f"        + rsvp @{username} ({response})")
                    else:
                        print(f"        ~ rsvp @{username} (exists)")


async def _run(session: AsyncSession) -> None:
    hashed_pw = hash_password(SEED_PASSWORD)

    print("\n[users]")
    users = await _seed_users(session, hashed_pw)
    await session.commit()

    print("\n[friendships]")
    await _seed_friendships(session, users)
    await session.commit()

    print("\n[games]")
    await _seed_games(session, users)
    await session.commit()

    print("\n[groups / locations / series / occurrences / rsvps]")
    await _seed_groups(session, users)
    await session.commit()


async def main() -> None:
    host_hint = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"Seeding: {host_hint}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        await _run(session)

    await engine.dispose()

    print("\nDone. Seed accounts (password: Seed@1234!):")
    for u in USERS:
        print(f"  {u['email']:<30}  @{u['username']}")


if __name__ == "__main__":
    asyncio.run(main())
