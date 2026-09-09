from __future__ import annotations

import time
from uuid import uuid4

import jwt
from fastapi import Request

from widget_bff.config import Settings
from widget_bff.models import HostRecord, SessionClaims


class SessionTokenError(Exception):
    pass


def create_anonymous_token(
    settings: Settings, host: HostRecord
) -> tuple[str, SessionClaims]:
    now = int(time.time())
    claims = SessionClaims(
        iss=settings.jwt_issuer,
        aud=settings.jwt_audience,
        sub=f"anonymous:{uuid4()}",
        sid=uuid4(),
        jti=uuid4(),
        partner_id=host.partner_id,
        host_id=host.host_id,
        scopes=["advisory:chat"],
        amr=["anonymous"],
        iat=now,
        nbf=now,
        exp=now + settings.anonymous_ttl_seconds,
    )
    token = jwt.encode(
        claims.model_dump(mode="json"),
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, claims


def decode_session_token(token: str, settings: Settings) -> SessionClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
        return SessionClaims.model_validate(payload)
    except (jwt.PyJWTError, ValueError) as exc:
        raise SessionTokenError("invalid or expired widget session") from exc


def bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise SessionTokenError("a bearer token is required")
    return token
