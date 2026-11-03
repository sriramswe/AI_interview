import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from core import database, models
bearer_scheme = HTTPBearer(auto_error=False)
_PASSWORD_ITERATIONS = 310_000
_TOKEN_SECRET = os.getenv("JWT_SECRET_KEY")


def _secret() -> bytes:
    secret = _TOKEN_SECRET or os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured before generating or verifying tokens."
        )
    return secret.encode("utf-8")


def _encode_segment(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_segment(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return (
        f"pbkdf2_sha256${_PASSWORD_ITERATIONS}"
        f"${_encode_segment(salt)}${_encode_segment(digest)}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iteration_text, salt_text, expected_text = password_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iteration_text)
        if iterations < 1:
            return False
        salt = _decode_segment(salt_text)
        expected = _decode_segment(expected_text)
    except (AttributeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def create_access_token(
    data: dict,
    expires_in_seconds: int | None = None,
) -> str:
    if expires_in_seconds is None:
        try:
            expires_in_seconds = int(
                os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", str(24 * 60 * 60))
            )
        except ValueError as error:
            raise RuntimeError(
                "ACCESS_TOKEN_EXPIRE_SECONDS must be a positive integer."
            ) from error
    if expires_in_seconds <= 0:
        raise ValueError("Token expiry must be positive.")
    now = int(time.time())
    header = _encode_segment(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload_data = {
        **data,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    payload = _encode_segment(
        json.dumps(payload_data, separators=(",", ":"), ensure_ascii=True).encode()
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    signature = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_encode_segment(signature)}"


def _decode_access_token(token: str) -> dict:
    try:
        header_part, payload_part, signature_part = token.split(".")
        header = json.loads(_decode_segment(header_part))
        payload = json.loads(_decode_segment(payload_part))
        signature = _decode_segment(signature_part)
        if header != {"alg": "HS256", "typ": "JWT"}:
            raise ValueError("Unsupported token header.")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid token signature.")
        if int(payload["exp"]) <= int(time.time()) or not payload.get("sub"):
            raise ValueError("Token has expired or has no subject.")
        return payload
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(database.get_db),
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_access_token(credentials.credentials)
    token_id = payload.get("jti")
    if token_id and db.get(models.RevokedToken, token_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def revoke_access_token(payload: dict, db: Session) -> None:
    token_id = payload.get("jti")
    if not token_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in again before logging out.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db.execute(
        delete(models.RevokedToken).where(
            models.RevokedToken.expires_at <= datetime.now(timezone.utc)
        )
    )
    if db.get(models.RevokedToken, token_id) is None:
        db.add(
            models.RevokedToken(
                jti=token_id,
                expires_at=datetime.fromtimestamp(
                    int(payload["exp"]), timezone.utc
                ),
            )
        )
        db.commit()


def get_current_user(
    payload: dict = Depends(get_current_token_payload),
    db: Session = Depends(database.get_db),
) -> models.User:
    user = db.scalar(select(models.User).where(models.User.email == payload["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_control = db.get(models.UserAccessControl, user.id)
    if access_control and access_control.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is suspended. Contact support for assistance.",
        )
    return user
