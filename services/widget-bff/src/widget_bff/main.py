from __future__ import annotations

import asyncio
import html
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, StreamingResponse

from widget_bff import __version__
from widget_bff.audit import audit_chat
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
from widget_bff.traffic import (
    GenerationInProgress,
    RateLimitExceeded,
    TrafficControlUnavailable,
    TrafficGuard,
    build_traffic_guard,
)

logger = logging.getLogger("widget_bff")


def _sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def create_app(
    settings: Settings | None = None,
    gateway: ChatGateway | None = None,
    traffic_guard: TrafficGuard | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    registry = HostRegistry.from_json(resolved_settings.hosts_json)
    resolved_gateway = gateway or AmulChatGateway(resolved_settings)
    resolved_traffic_guard = traffic_guard or build_traffic_guard(resolved_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            await resolved_traffic_guard.close()
            close_gateway = getattr(resolved_gateway, "close", None)
            if close_gateway is not None:
                await close_gateway()

    app = FastAPI(
        title="Amul AI Widget BFF",
        version=__version__,
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
    app.state.traffic_guard = resolved_traffic_guard

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        supplied_request_id = request.headers.get("x-request-id")
        try:
            request_id = (
                str(UUID(supplied_request_id)) if supplied_request_id else str(uuid4())
            )
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
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
            "version": __version__,
            "upstream_configured": resolved_gateway.configured,
            "traffic_control_backend": resolved_traffic_guard.backend,
        }

    @app.get("/api/v1/ready", include_in_schema=False)
    async def ready(request: Request):
        if not resolved_gateway.configured or not await resolved_traffic_guard.ready():
            return problem_response(
                status=503,
                code="dependency_unavailable",
                title="Widget backend is not ready",
                request_id=request.state.request_id,
                retry_after=10,
            )
        return {"status": "ready"}

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
        if (
            payload.conversation_id is not None
            and payload.conversation_id != claims.sid
        ):
            return problem_response(
                status=403,
                code="invalid_conversation",
                title="Conversation does not belong to this session",
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

        try:
            lease = await resolved_traffic_guard.start_turn(claims)
        except RateLimitExceeded as exc:
            audit_chat(
                claims=claims,
                request_id=request.state.request_id,
                outcome="rate_limited",
            )
            return problem_response(
                status=429,
                code="rate_limited",
                title="Too many advisory requests",
                request_id=request.state.request_id,
                retry_after=exc.retry_after,
            )
        except GenerationInProgress as exc:
            audit_chat(
                claims=claims,
                request_id=request.state.request_id,
                outcome="generation_in_progress",
            )
            return problem_response(
                status=429,
                code="generation_in_progress",
                title="An advisory response is already being generated",
                request_id=request.state.request_id,
                retry_after=exc.retry_after,
            )
        except TrafficControlUnavailable:
            logger.exception(
                "traffic control unavailable request_id=%s",
                request.state.request_id,
            )
            audit_chat(
                claims=claims,
                request_id=request.state.request_id,
                outcome="traffic_control_unavailable",
            )
            return problem_response(
                status=503,
                code="dependency_unavailable",
                title="Widget backend is temporarily unavailable",
                request_id=request.state.request_id,
                retry_after=10,
            )

        conversation_id = payload.conversation_id or claims.sid
        started_at = time.monotonic()

        async def events() -> AsyncIterator[str]:
            outcome = "completed"
            try:
                yield _sse("turn.started", {"conversation_id": str(conversation_id)})
                async for chunk in resolved_gateway.stream(payload, claims):
                    yield _sse("message.delta", {"text": chunk})
                yield _sse(
                    "message.completed",
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": str(payload.message_id),
                    },
                )
            except asyncio.CancelledError:
                outcome = "cancelled"
                raise
            except (ChatGatewayError, httpx.HTTPError, KeyError):
                outcome = "upstream_failed"
                logger.exception(
                    "upstream chat failed request_id=%s",
                    request.state.request_id,
                )
                problem = {
                    "type": "https://widget.amulai.in/problems/upstream-failed",
                    "title": "Advisory service failed",
                    "status": 502,
                    "code": "upstream_failed",
                    "request_id": request.state.request_id,
                    "detail": "The advisory service could not complete the request.",
                }
                yield _sse("error", problem)
            finally:
                await resolved_traffic_guard.finish_turn(lease)
                audit_chat(
                    claims=claims,
                    request_id=request.state.request_id,
                    outcome=outcome,
                    duration_ms=int((time.monotonic() - started_at) * 1000),
                )

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
