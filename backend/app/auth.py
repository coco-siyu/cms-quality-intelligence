import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException

from app.config import Settings, get_settings

SESSION_COOKIE_NAME = "cmsqi_admin_session"


@dataclass(frozen=True)
class AdminIdentity:
    username: str


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def admin_auth_is_configured(settings: Settings) -> bool:
    return bool(
        settings.admin_username
        and settings.admin_password_hash
        and settings.admin_session_secret
    )


def hash_admin_password(password: str, *, salt: bytes | None = None) -> str:
    password_salt = salt or __import__("secrets").token_bytes(16)
    cost, block_size, parallelism = 16384, 8, 1
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=password_salt,
        n=cost,
        r=block_size,
        p=parallelism,
        dklen=32,
    )
    return "$".join(
        [
            "scrypt",
            str(cost),
            str(block_size),
            str(parallelism),
            _encode(password_salt),
            _encode(digest),
        ]
    )


def verify_admin_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, cost, block_size, parallelism, salt, expected = encoded_hash.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt),
            n=int(cost),
            r=int(block_size),
            p=int(parallelism),
            dklen=len(_decode(expected)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, _decode(expected))


def create_admin_session(username: str, settings: Settings, *, now: int | None = None) -> str:
    issued_at = int(time.time()) if now is None else now
    payload = _encode(
        json.dumps(
            {"username": username, "expires_at": issued_at + settings.admin_session_ttl_seconds},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    signature = hmac.new(
        settings.admin_session_secret.encode("utf-8"),
        payload.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload}.{_encode(signature)}"


def read_admin_session(
    token: str | None,
    settings: Settings,
    *,
    now: int | None = None,
) -> AdminIdentity | None:
    if not token or not admin_auth_is_configured(settings):
        return None
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(
            settings.admin_session_secret.encode("utf-8"),
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(signature), expected):
            return None
        data = json.loads(_decode(payload))
        current_time = int(time.time()) if now is None else now
        if data["expires_at"] <= current_time:
            return None
        if not hmac.compare_digest(str(data["username"]), settings.admin_username):
            return None
        return AdminIdentity(username=settings.admin_username)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AdminIdentity:
    identity = read_admin_session(session_cookie, settings)
    if identity is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "admin_authentication_required",
                "message": "A valid administrator session is required.",
                "details": [],
            },
        )
    return identity
