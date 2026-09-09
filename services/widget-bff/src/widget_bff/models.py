from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

Locale = Literal["en", "hi", "gu"]
Feature = Literal["advisory_chat", "voice_input"]


class HostRecord(BaseModel):
    partner_id: UUID
    partner_name: str
    host_id: str = Field(pattern=r"^AMULAI-HOST-[0-9a-f]{8}$")
    status: Literal["active", "disabled"] = "active"
    allowed_frame_origins: Annotated[list[str], Field(min_length=1)]
    features: Annotated[list[Feature], Field(min_length=1)]
    locales: Annotated[list[Locale], Field(min_length=1)]
    default_locale: Locale
    rate_limit_tier: str = "standard"


class PublicHostConfig(BaseModel):
    host_id: str
    partner_name: str
    features: list[Feature]
    locales: list[Locale]
    default_locale: Locale


class AnonymousSessionRequest(BaseModel):
    host_id: str = Field(pattern=r"^AMULAI-HOST-[0-9a-f]{8}$")
    locale: Locale


class AnonymousSessionResponse(BaseModel):
    session_id: UUID
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    features: list[Feature]


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message_id: UUID
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    locale: Locale


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    code: str
    request_id: str
    detail: str | None = None
    retry_after: int | None = None


class SessionClaims(BaseModel):
    iss: str
    aud: str
    sub: str
    sid: UUID
    jti: UUID
    partner_id: UUID
    host_id: str
    scopes: list[str]
    amr: list[str]
    iat: int
    nbf: int
    exp: int
