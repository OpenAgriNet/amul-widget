from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from redis.asyncio import Redis
from redis.exceptions import RedisError

from widget_bff.config import Settings
from widget_bff.models import SessionClaims

logger = logging.getLogger("uvicorn.error")

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

RELEASE_LEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int):
        super().__init__("advisory turn limit exceeded")
        self.retry_after = max(retry_after, 1)


class GenerationInProgress(Exception):
    def __init__(self, retry_after: int = 2):
        super().__init__("a generation is already active for this session")
        self.retry_after = retry_after


class TrafficControlUnavailable(Exception):
    pass


@dataclass(frozen=True)
class GenerationLease:
    key: str
    value: str


class TrafficGuard(Protocol):
    @property
    def backend(self) -> str: ...

    async def ready(self) -> bool: ...

    async def start_turn(self, claims: SessionClaims) -> GenerationLease: ...

    async def finish_turn(self, lease: GenerationLease) -> None: ...

    async def close(self) -> None: ...


class RedisTrafficGuard:
    def __init__(self, settings: Settings):
        if settings.redis_url is None:
            raise ValueError("RedisTrafficGuard requires WIDGET_REDIS_URL")
        self._client = Redis.from_url(
            str(settings.redis_url),
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=2.0,
            health_check_interval=30,
        )
        self._prefix = settings.redis_key_prefix
        self._turn_limit = settings.advisory_turn_limit
        self._turn_window = settings.advisory_turn_window_seconds
        self._lease_seconds = settings.generation_lease_seconds

    @property
    def backend(self) -> str:
        return "redis"

    def _key(self, kind: str, claims: SessionClaims) -> str:
        return f"{self._prefix}:{kind}:{claims.host_id}:{claims.sid}"

    async def ready(self) -> bool:
        try:
            return bool(await self._client.ping())
        except RedisError:
            return False

    async def start_turn(self, claims: SessionClaims) -> GenerationLease:
        rate_key = self._key("turns", claims)
        lease_key = self._key("generation", claims)
        lease_value = str(uuid4())
        try:
            current, ttl = await self._client.eval(
                RATE_LIMIT_SCRIPT,
                1,
                rate_key,
                self._turn_window,
            )
            if int(current) > self._turn_limit:
                raise RateLimitExceeded(int(ttl))
            acquired = await self._client.set(
                lease_key,
                lease_value,
                ex=self._lease_seconds,
                nx=True,
            )
        except (RateLimitExceeded, GenerationInProgress):
            raise
        except RedisError as exc:
            raise TrafficControlUnavailable(
                "traffic control store unavailable"
            ) from exc

        if not acquired:
            raise GenerationInProgress()
        return GenerationLease(key=lease_key, value=lease_value)

    async def finish_turn(self, lease: GenerationLease) -> None:
        try:
            await self._client.eval(
                RELEASE_LEASE_SCRIPT,
                1,
                lease.key,
                lease.value,
            )
        except RedisError:
            logger.exception("failed to release generation lease")

    async def close(self) -> None:
        await self._client.aclose()


class MemoryTrafficGuard:
    """Development and test fallback; production requires Redis."""

    def __init__(self, settings: Settings):
        self._turn_limit = settings.advisory_turn_limit
        self._turn_window = settings.advisory_turn_window_seconds
        self._lease_seconds = settings.generation_lease_seconds
        self._turns: dict[tuple[str, UUID], tuple[int, float]] = {}
        self._leases: dict[tuple[str, UUID], tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    @property
    def backend(self) -> str:
        return "memory"

    async def ready(self) -> bool:
        return True

    async def start_turn(self, claims: SessionClaims) -> GenerationLease:
        now = time.monotonic()
        identity = (claims.host_id, claims.sid)
        async with self._lock:
            count, reset_at = self._turns.get(identity, (0, now + self._turn_window))
            if now >= reset_at:
                count, reset_at = 0, now + self._turn_window
            count += 1
            self._turns[identity] = (count, reset_at)
            if count > self._turn_limit:
                raise RateLimitExceeded(int(reset_at - now) + 1)

            existing = self._leases.get(identity)
            if existing and existing[1] > now:
                raise GenerationInProgress()
            lease_value = str(uuid4())
            self._leases[identity] = (lease_value, now + self._lease_seconds)
        return GenerationLease(
            key=f"memory:{claims.host_id}:{claims.sid}",
            value=lease_value,
        )

    async def finish_turn(self, lease: GenerationLease) -> None:
        _, host_id, raw_session_id = lease.key.split(":", 2)
        identity = (host_id, UUID(raw_session_id))
        async with self._lock:
            existing = self._leases.get(identity)
            if existing and existing[0] == lease.value:
                self._leases.pop(identity, None)

    async def close(self) -> None:
        return None


def build_traffic_guard(settings: Settings) -> TrafficGuard:
    if settings.redis_url is not None:
        return RedisTrafficGuard(settings)
    return MemoryTrafficGuard(settings)
