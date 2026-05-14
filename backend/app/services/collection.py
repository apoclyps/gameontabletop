from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


async def is_friend(session: AsyncSession, user_a_id, user_b_id) -> bool:
    """Return True if user_a and user_b have an accepted friendship."""
    from app.models.collection import UserFriendship

    result = await session.execute(
        select(UserFriendship).where(
            or_(
                and_(
                    UserFriendship.requester_id == user_a_id,
                    UserFriendship.addressee_id == user_b_id,
                ),
                and_(
                    UserFriendship.requester_id == user_b_id,
                    UserFriendship.addressee_id == user_a_id,
                ),
            ),
            UserFriendship.status == "accepted",
        )
    )
    return result.scalar_one_or_none() is not None


async def get_friend_ids(session: AsyncSession, user_id) -> list:
    """Return list of user IDs that are accepted friends of user_id."""
    from app.models.collection import UserFriendship

    result = await session.execute(
        select(UserFriendship).where(
            or_(
                UserFriendship.requester_id == user_id,
                UserFriendship.addressee_id == user_id,
            ),
            UserFriendship.status == "accepted",
        )
    )
    friendships = result.scalars().all()
    return [
        f.addressee_id if f.requester_id == user_id else f.requester_id
        for f in friendships
    ]
