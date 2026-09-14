from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Protocol

import httpx
import jwt

from widget_bff.config import Settings
from widget_bff.models import ChatRequest, SessionClaims


class ChatGatewayError(Exception):
    pass


class ChatGatewayNotConfigured(ChatGatewayError):
    pass


class ChatGateway(Protocol):
    @property
    def configured(self) -> bool: ...

    def stream(
        self, request: ChatRequest, claims: SessionClaims
    ) -> AsyncIterator[str]: ...

    async def close(self) -> None: ...


class AmulChatGateway:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient | None = None,
    ):
        self._base_url = (
            str(settings.amul_api_base_url).rstrip("/")
            if settings.amul_api_base_url
            else None
        )
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(settings.upstream_timeout_seconds, connect=10.0),
            trust_env=False,
        )
        self._owns_client = client is None
        self._cached_token: str | None = None
        self._cached_token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return self._base_url is not None

    async def _upstream_token(self, *, force_refresh: bool = False) -> str:
        now = time.time()
        if (
            not force_refresh
            and self._cached_token
            and self._cached_token_expires_at > now + 30
        ):
            return self._cached_token

        async with self._token_lock:
            now = time.time()
            if (
                not force_refresh
                and self._cached_token
                and self._cached_token_expires_at > now + 30
            ):
                return self._cached_token
            if not self._base_url:
                raise ChatGatewayNotConfigured("AMUL chat API is not configured")
            response = await self._client.post(f"{self._base_url}/api/auth/anonymous")
            response.raise_for_status()
            token = response.json()["access_token"]
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                expires_at = float(payload["exp"])
            except (jwt.PyJWTError, KeyError, TypeError, ValueError):
                expires_at = now + 300
            self._cached_token = token
            self._cached_token_expires_at = expires_at
            return token

    async def stream(
        self, request: ChatRequest, claims: SessionClaims
    ) -> AsyncIterator[str]:
        if not self._base_url:
            raise ChatGatewayNotConfigured("AMUL chat API is not configured")

        params = {
            "session_id": str(request.conversation_id or claims.sid),
            "query": request.text,
            "source_lang": request.locale,
            "target_lang": request.locale,
            "channel": "web",
        }
        for attempt in range(2):
            upstream_token = await self._upstream_token(force_refresh=attempt > 0)
            async with self._client.stream(
                "GET",
                f"{self._base_url}/api/chat/",
                params=params,
                headers={"Authorization": f"Bearer {upstream_token}"},
            ) as response:
                if response.status_code == 401 and attempt == 0:
                    self._cached_token = None
                    continue
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk
                return

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
