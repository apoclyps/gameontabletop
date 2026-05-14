import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.admin import AdminRoleUpdate, AdminUserItem, AdminUsersPage

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=AdminUsersPage,
    summary="List all users (admin only)",
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Admin access required"},
    },
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size

    total_result = await session.execute(select(func.count()).select_from(User))
    total = total_result.scalar_one()

    result = await session.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = result.scalars().all()

    return AdminUsersPage(
        users=[AdminUserItem.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserItem,
    summary="Update a user's admin role (admin only)",
    responses={
        400: {"description": "Cannot demote yourself"},
        401: {"description": "Unauthorized"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def update_user_role(
    user_id: uuid.UUID,
    body: AdminRoleUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if user_id == current_user.id and not body.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote your own admin role",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_admin = body.is_admin
    await session.commit()
    await session.refresh(user)
    return AdminUserItem.model_validate(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disable a user account (admin only)",
    responses={
        400: {"description": "Cannot disable your own account"},
        401: {"description": "Unauthorized"},
        403: {"description": "Admin access required"},
        404: {"description": "User not found"},
    },
)
async def disable_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot disable your own account",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = False
    await session.commit()
