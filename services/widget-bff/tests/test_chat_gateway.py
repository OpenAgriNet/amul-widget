from __future__ import annotations

import asyncio
import time
from uuid import uuid4

import httpx
import jwt

from widget_bff.chat_gateway import AmulChatGateway
from widget_bff.config import Settings
from widget_bff.models import ChatRequest, SessionClaims


def test_gateway_reuses_upstream_anonymous_token() -> None:
    async def scenario() -> None:
        auth_calls = 0
        upstream_token = jwt.encode(
            {"exp": int(time.time()) + 3600},
            "upstream-test-secret-with-enough-entropy",
            algorithm="HS256",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal auth_calls
            if request.url.path == "/api/auth/anonymous":
                auth_calls += 1
                return httpx.Response(200, json={"access_token": upstream_token})
            if request.url.path == "/api/chat/":
                assert request.headers["authorization"] == f"Bearer {upstream_token}"
                return httpx.Response(200, text="Useful advice")
            return httpx.Response(404)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = AmulChatGateway(
            Settings(amul_api_base_url="https://upstream.example"),
            client=client,
        )
        now = int(time.time())
        session_claims = SessionClaims(
            iss="https://widget.amulai.in",
            aud="amul-widget-bff",
            sub="anonymous:test",
            sid=uuid4(),
            jti=uuid4(),
            partner_id=uuid4(),
            host_id="AMULAI-HOST-6c48b031",
            scopes=["advisory:chat"],
            amr=["anonymous"],
            iat=now,
            nbf=now,
            exp=now + 900,
        )
        request = ChatRequest(
            conversation_id=None,
            message_id=uuid4(),
            text="How do I prevent mastitis?",
            locale="en",
        )

        first = "".join(
            [chunk async for chunk in gateway.stream(request, session_claims)]
        )
        second = "".join(
            [chunk async for chunk in gateway.stream(request, session_claims)]
        )

        assert first == "Useful advice"
        assert second == "Useful advice"
        assert auth_calls == 1
        await client.aclose()

    asyncio.run(scenario())
