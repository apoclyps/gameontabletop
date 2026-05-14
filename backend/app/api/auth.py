import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.services.email import send_password_reset_email, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
    summary="Register a new account",
    responses={
        409: {"description": "Email or username already registered"},
        422: {"description": "Validation error"},
    },
)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(
        select(User).where(
            (User.email == body.email) | (User.username == body.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_verification_token(user.email)
    send_verification_email(user.email, token)

    return {
        "message": "Registration successful. Check your email to verify your account."
    }


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and obtain JWT tokens",
    responses={
        401: {"description": "Invalid credentials"},
        403: {"description": "Email not verified or account disabled"},
        422: {"description": "Validation error"},
    },
)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled"
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out (client-side token discard)",
)
async def logout():
    # Tokens are stateless; client discards them.
    return {"message": "Logged out"}


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a refresh token",
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address via token from confirmation email",
    responses={
        400: {"description": "Invalid or expired verification token"},
        404: {"description": "User not found"},
    },
)
async def verify_email(token: str, session: AsyncSession = Depends(get_session)):
    try:
        payload = decode_token(token)
        if payload.get("type") != "verify":
            raise ValueError("wrong token type")
        email: str = payload["sub"]
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_verified:
        user.is_verified = True
        await session.commit()

    return {"message": "Email verified successfully"}


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
    description=(
        "Always returns 200 to prevent email enumeration. "
        "A reset link is sent only if the address is registered."
    ),
)
async def forgot_password(
    body: ForgotPasswordRequest, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        token = create_password_reset_token(str(user.id))
        send_password_reset_email(user.email, token)
    # Always 200 to prevent email enumeration
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using a reset token",
    responses={
        400: {"description": "Invalid or expired reset token"},
        404: {"description": "User not found"},
    },
)
async def reset_password(
    body: ResetPasswordRequest, session: AsyncSession = Depends(get_session)
):
    try:
        payload = decode_token(body.token)
        if payload.get("type") != "reset":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.hashed_password = hash_password(body.new_password)
    await session.commit()
    return {"message": "Password reset successful"}
