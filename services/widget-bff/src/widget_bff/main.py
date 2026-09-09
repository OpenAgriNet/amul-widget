from __future__ import annotations

import html
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, StreamingResponse

from widget_bff.chat_gateway import (
    AmulChatGateway,
    ChatGateway,
    ChatGatewayError,
)
from widget_bff.config import Settings
from widget_bff.hosts import HostRegistry
from widget_bff.models import (
    AnonymousSessionRequest,
    AnonymousSessionResponse,
    ChatRequest,
    PublicHostConfig,
    SessionClaims,
)
from widget_bff.problems import problem_response
from widget_bff.security import (
    SessionTokenError,
    bearer_token,
    create_anonymous_token,
    decode_session_token,
)


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def create_app(
    settings: Settings | None = None,
    gateway: ChatGateway | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    registry = HostRegistry.from_json(resolved_settings.hosts_json)
    resolved_gateway = gateway or AmulChatGateway(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(
        title="Amul AI Widget BFF",
        version="0.1.0",
        docs_url="/docs" if resolved_settings.environment != "production" else None,
        redoc_url=None,
        openapi_url=(
            "/openapi.json" if resolved_settings.environment != "production" else None
        ),
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.host_registry = registry
    app.state.chat_gateway = resolved_gateway

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def active_host(host_id: str):
        host = registry.get_active(host_id)
        if host is None:
            return None
        return host

    async def current_session(request: Request) -> SessionClaims:
        claims = decode_session_token(bearer_token(request), resolved_settings)
        host = active_host(claims.host_id)
        if host is None or str(host.partner_id) != str(claims.partner_id):
            raise SessionTokenError("widget host is no longer active")
        return claims

    @app.exception_handler(SessionTokenError)
    async def session_token_error(request: Request, exc: SessionTokenError):
        return problem_response(
            status=401,
            code="invalid_session",
            title="Invalid widget session",
            detail=str(exc),
            request_id=request.state.request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError):
        return problem_response(
            status=422,
            code="validation_error",
            title="Request validation failed",
            request_id=request.state.request_id,
        )

    @app.get("/api/v1/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "amul-widget-bff",
            "version": "0.1.0",
            "upstream_configured": resolved_gateway.configured,
        }

    @app.get(
        "/api/v1/hosts/{host_id}/config",
        response_model=PublicHostConfig,
    )
    async def host_config(host_id: str, request: Request):
        host = active_host(host_id)
        if host is None:
            return problem_response(
                status=404,
                code="host_not_found",
                title="Widget host not found",
                request_id=request.state.request_id,
            )
        return registry.public_config(host)

    @app.post(
        "/api/v1/sessions/anonymous",
        response_model=AnonymousSessionResponse,
        status_code=201,
    )
    async def anonymous_session(payload: AnonymousSessionRequest, request: Request):
        host = active_host(payload.host_id)
        if host is None or payload.locale not in host.locales:
            return problem_response(
                status=404,
                code="host_not_found",
                title="Widget host not found",
                request_id=request.state.request_id,
            )
        token, claims = create_anonymous_token(resolved_settings, host)
        return AnonymousSessionResponse(
            session_id=claims.sid,
            access_token=token,
            expires_in=resolved_settings.anonymous_ttl_seconds,
            features=host.features,
        )

    idempotency_header = Header(alias="Idempotency-Key")
    session_dependency = Depends(current_session)

    @app.post("/api/v1/chat/stream")
    async def chat_stream(
        payload: ChatRequest,
        request: Request,
        idempotency_key: UUID = idempotency_header,
        claims: SessionClaims = session_dependency,
    ):
        del idempotency_key
        if "advisory:chat" not in claims.scopes:
            return problem_response(
                status=403,
                code="insufficient_scope",
                title="Insufficient scope",
                request_id=request.state.request_id,
            )
        if not resolved_gateway.configured:
            return problem_response(
                status=503,
                code="upstream_unavailable",
                title="Advisory service unavailable",
                detail="The upstream advisory service is not configured.",
                request_id=request.state.request_id,
                retry_after=30,
            )

        conversation_id = payload.conversation_id or claims.sid

        async def events() -> AsyncIterator[str]:
            yield _sse("turn.started", {"conversation_id": str(conversation_id)})
            try:
                async for chunk in resolved_gateway.stream(payload, claims):
                    yield _sse("message.delta", {"text": chunk})
                yield _sse(
                    "message.completed",
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": str(payload.message_id),
                    },
                )
            except (ChatGatewayError, httpx.HTTPError, KeyError) as exc:
                problem = {
                    "type": "https://widget.amulai.in/problems/upstream-failed",
                    "title": "Advisory service failed",
                    "status": 502,
                    "code": "upstream_failed",
                    "request_id": request.state.request_id,
                    "detail": str(exc),
                }
                yield _sse("error", problem)

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/embed/{host_id}", response_class=HTMLResponse)
    async def embed(host_id: str, request: Request):
        host = active_host(host_id)
        if host is None:
            return problem_response(
                status=404,
                code="host_not_found",
                title="Widget host not found",
                request_id=request.state.request_id,
            )
        frame_ancestors = " ".join(host.allowed_frame_origins)
        document = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="amul-widget-host-id" content="{html.escape(host.host_id)}" />
    <title>Amul AI · {html.escape(host.partner_name)}</title>
    <link rel="icon" type="image/svg+xml" href="/AmulLogo.svg" />
    <link rel="stylesheet" href="/assets/widget-app.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/widget-app.js"></script>
  </body>
</html>"""
        return HTMLResponse(
            document,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": (
                    "default-src 'none'; "
                    "script-src 'self'; style-src 'self'; img-src 'self' data:; "
                    "font-src 'self'; connect-src 'self'; object-src 'none'; "
                    f"base-uri 'none'; form-action 'none'; frame-ancestors {frame_ancestors}"
                ),
                "Permissions-Policy": "microphone=(self)",
                "Referrer-Policy": "no-referrer",
            },
        )

    return app


app = create_app()
