from __future__ import annotations

import jwt
from fastapi.testclient import TestClient

from widget_bff.config import Settings
from widget_bff.main import create_app
from widget_bff.models import ChatRequest, SessionClaims


class FakeChatGateway:
    configured = True

    async def stream(self, _: ChatRequest, __: SessionClaims):
        yield "Useful "
        yield "advice"


def client() -> tuple[TestClient, Settings]:
    settings = Settings(
        environment="test", jwt_secret="test-secret-with-enough-entropy-1234"
    )
    return TestClient(create_app(settings)), settings


def issue_session(test_client: TestClient) -> dict:
    response = test_client.post(
        "/api/v1/sessions/anonymous",
        json={"host_id": "AMULAI-HOST-6c48b031", "locale": "gu"},
    )
    assert response.status_code == 201
    return response.json()


def test_health_is_public() -> None:
    test_client, _ = client()
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["traffic_control_backend"] == "memory"


def test_ready_requires_the_upstream() -> None:
    test_client, _ = client()
    response = test_client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "dependency_unavailable"


def test_public_host_config_does_not_expose_origins_or_partner_id() -> None:
    test_client, _ = client()
    response = test_client.get("/api/v1/hosts/AMULAI-HOST-6c48b031/config")
    assert response.status_code == 200
    body = response.json()
    assert body["locales"] == ["gu", "hi", "en"]
    assert "allowed_frame_origins" not in body
    assert "partner_id" not in body


def test_unknown_host_uses_problem_details() -> None:
    test_client, _ = client()
    response = test_client.get("/api/v1/hosts/AMULAI-HOST-00000000/config")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "host_not_found"


def test_anonymous_session_is_short_lived_and_host_scoped() -> None:
    test_client, settings = client()
    session = issue_session(test_client)
    claims = jwt.decode(
        session["access_token"],
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert session["expires_in"] == 900
    assert claims["host_id"] == "AMULAI-HOST-6c48b031"
    assert claims["scopes"] == ["advisory:chat"]
    assert claims["amr"] == ["anonymous"]


def test_chat_requires_widget_session() -> None:
    test_client, _ = client()
    response = test_client.post(
        "/api/v1/chat/stream",
        headers={"Idempotency-Key": "eac2b3fe-bd25-4ff4-a023-cc91536005d0"},
        json={
            "conversation_id": None,
            "message_id": "20a8d4c2-009a-457c-ace2-bced07a4d7cc",
            "text": "How do I prevent mastitis?",
            "locale": "en",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_session"


def test_chat_rejects_conversation_from_another_session() -> None:
    settings = Settings(
        environment="test", jwt_secret="test-secret-with-enough-entropy-1234"
    )
    test_client = TestClient(create_app(settings, gateway=FakeChatGateway()))
    session = issue_session(test_client)
    response = test_client.post(
        "/api/v1/chat/stream",
        headers={
            "Authorization": f"Bearer {session['access_token']}",
            "Idempotency-Key": "eac2b3fe-bd25-4ff4-a023-cc91536005d0",
        },
        json={
            "conversation_id": "e0df4aac-eeb9-46c8-bbdb-f4a8ccbe04ae",
            "message_id": "20a8d4c2-009a-457c-ace2-bced07a4d7cc",
            "text": "How do I prevent mastitis?",
            "locale": "en",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "invalid_conversation"


def test_chat_returns_typed_503_when_upstream_is_not_configured() -> None:
    test_client, _ = client()
    session = issue_session(test_client)
    response = test_client.post(
        "/api/v1/chat/stream",
        headers={
            "Authorization": f"Bearer {session['access_token']}",
            "Idempotency-Key": "eac2b3fe-bd25-4ff4-a023-cc91536005d0",
        },
        json={
            "conversation_id": None,
            "message_id": "20a8d4c2-009a-457c-ace2-bced07a4d7cc",
            "text": "How do I prevent mastitis?",
            "locale": "en",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "upstream_unavailable"


def test_embed_shell_has_host_specific_frame_policy() -> None:
    test_client, _ = client()
    response = test_client.get("/embed/AMULAI-HOST-6c48b031")
    assert response.status_code == 200
    assert (
        "frame-ancestors https://sarlaben.ai"
        in response.headers["content-security-policy"]
    )
    assert response.headers["permissions-policy"] == "microphone=(self)"
    assert "/assets/widget-app.js" in response.text


def test_chat_stream_uses_versioned_sse_events() -> None:
    settings = Settings(
        environment="test", jwt_secret="test-secret-with-enough-entropy-1234"
    )
    test_client = TestClient(create_app(settings, gateway=FakeChatGateway()))
    session = issue_session(test_client)
    response = test_client.post(
        "/api/v1/chat/stream",
        headers={
            "Authorization": f"Bearer {session['access_token']}",
            "Idempotency-Key": "eac2b3fe-bd25-4ff4-a023-cc91536005d0",
        },
        json={
            "conversation_id": None,
            "message_id": "20a8d4c2-009a-457c-ace2-bced07a4d7cc",
            "text": "How do I prevent mastitis?",
            "locale": "en",
        },
    )
    assert response.status_code == 200
    assert "event: turn.started" in response.text
    assert 'event: message.delta\ndata: {"text":"Useful "}' in response.text
    assert "event: message.completed" in response.text


def test_chat_enforces_per_session_turn_limit() -> None:
    settings = Settings(
        environment="test",
        jwt_secret="test-secret-with-enough-entropy-1234",
        advisory_turn_limit=1,
    )
    test_client = TestClient(create_app(settings, gateway=FakeChatGateway()))
    session = issue_session(test_client)
    headers = {
        "Authorization": f"Bearer {session['access_token']}",
        "Idempotency-Key": "eac2b3fe-bd25-4ff4-a023-cc91536005d0",
    }
    payload = {
        "conversation_id": None,
        "message_id": "20a8d4c2-009a-457c-ace2-bced07a4d7cc",
        "text": "How do I prevent mastitis?",
        "locale": "en",
    }

    assert (
        test_client.post(
            "/api/v1/chat/stream", headers=headers, json=payload
        ).status_code
        == 200
    )
    response = test_client.post("/api/v1/chat/stream", headers=headers, json=payload)

    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert int(response.headers["retry-after"]) > 0


def test_untrusted_request_id_is_replaced() -> None:
    test_client, _ = client()
    response = test_client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "not-a-uuid-forged-log-line"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "not-a-uuid-forged-log-line"


def test_validation_errors_use_problem_details() -> None:
    test_client, _ = client()
    response = test_client.post(
        "/api/v1/sessions/anonymous",
        json={"host_id": "not-a-host", "locale": "gu"},
    )
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
