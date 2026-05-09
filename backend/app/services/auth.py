from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(payload: dict, expire_delta: timedelta) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(UTC) + expire_delta
    return jwt.encode(data, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def create_access_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def create_verification_token(email: str) -> str:
    return _create_token(
        {"sub": email, "type": "verify"},
        timedelta(hours=settings.verification_token_expire_hours),
    )


def create_password_reset_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "reset"},
        timedelta(hours=settings.password_reset_expire_hours),
    )
