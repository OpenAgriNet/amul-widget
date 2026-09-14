from __future__ import annotations

import time
from uuid import uuid4

from widget_bff.audit import chat_audit_event
from widget_bff.models import SessionClaims


def test_chat_audit_excludes_tokens_and_message_content() -> None:
    now = int(time.time())
    claims = SessionClaims(
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

    event = chat_audit_event(
        claims=claims,
        request_id=str(uuid4()),
        outcome="completed",
        duration_ms=123,
    )

    assert event["event"] == "widget.chat"
    assert event["outcome"] == "completed"
    assert event["duration_ms"] == 123
    assert "token" not in event
    assert "text" not in event
