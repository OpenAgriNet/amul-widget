from __future__ import annotations

import json
import logging
from typing import Any

from widget_bff.models import SessionClaims

logger = logging.getLogger("uvicorn.error")


def chat_audit_event(
    *,
    claims: SessionClaims,
    request_id: str,
    outcome: str,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event": "widget.chat",
        "host_id": claims.host_id,
        "partner_id": str(claims.partner_id),
        "session_id": str(claims.sid),
        "request_id": request_id,
        "outcome": outcome,
    }
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    return event


def audit_chat(**kwargs: Any) -> None:
    logger.info(json.dumps(chat_audit_event(**kwargs), separators=(",", ":")))
