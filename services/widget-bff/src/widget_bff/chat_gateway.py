from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

import httpx

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


class AmulChatGateway:
    def __init__(self, settings: Settings):
        self._base_url = (
            str(settings.amul_api_base_url).rstrip("/")
            if settings.amul_api_base_url
            else None
        )
        self._timeout = settings.upstream_timeout_seconds

    @property
    def configured(self) -> bool:
        return self._base_url is not None

    async def stream(
        self, request: ChatRequest, claims: SessionClaims
    ) -> AsyncIterator[str]:
        if not self._base_url:
            raise ChatGatewayNotConfigured("AMUL chat API is not configured")

        timeout = httpx.Timeout(self._timeout, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            token_response = await client.post(f"{self._base_url}/api/auth/anonymous")
            token_response.raise_for_status()
            upstream_token = token_response.json()["access_token"]
            params = {
                "session_id": str(request.conversation_id or claims.sid),
                "query": request.text,
                "source_lang": request.locale,
                "target_lang": request.locale,
                "channel": "web",
            }
            async with client.stream(
                "GET",
                f"{self._base_url}/api/chat/",
                params=params,
                headers={"Authorization": f"Bearer {upstream_token}"},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk
