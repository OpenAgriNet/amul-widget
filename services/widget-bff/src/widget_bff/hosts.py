from __future__ import annotations

import json
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import TypeAdapter

from widget_bff.models import HostRecord, PublicHostConfig

DEFAULT_HOSTS = [
    HostRecord(
        partner_id=UUID("75997c54-7a1c-4f1a-9b38-dff392a8ae8c"),
        partner_name="Sarlaben",
        host_id="AMULAI-HOST-6c48b031",
        allowed_frame_origins=["https://sarlaben.ai"],
        features=["advisory_chat", "voice_input"],
        locales=["gu", "hi", "en"],
        default_locale="gu",
    )
]


def _validate_origin(origin: str) -> str:
    parsed = urlsplit(origin)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or parsed.port not in (None, 443)
    ):
        raise ValueError(f"invalid allowed frame origin: {origin}")
    return f"https://{parsed.hostname.lower()}"


class HostRegistry:
    def __init__(self, records: list[HostRecord]):
        normalized: dict[str, HostRecord] = {}
        for record in records:
            record.allowed_frame_origins = [
                _validate_origin(origin) for origin in record.allowed_frame_origins
            ]
            if record.default_locale not in record.locales:
                raise ValueError(
                    f"default locale is not enabled for host {record.host_id}"
                )
            if record.host_id in normalized:
                raise ValueError(f"duplicate widget host: {record.host_id}")
            normalized[record.host_id] = record
        self._records = normalized

    @classmethod
    def from_json(cls, raw: str | None) -> HostRegistry:
        if not raw:
            return cls([record.model_copy(deep=True) for record in DEFAULT_HOSTS])
        records = TypeAdapter(list[HostRecord]).validate_python(json.loads(raw))
        return cls(records)

    def get_active(self, host_id: str) -> HostRecord | None:
        record = self._records.get(host_id)
        return record if record and record.status == "active" else None

    @staticmethod
    def public_config(record: HostRecord) -> PublicHostConfig:
        return PublicHostConfig(
            host_id=record.host_id,
            partner_name=record.partner_name,
            features=record.features,
            locales=record.locales,
            default_locale=record.default_locale,
        )
