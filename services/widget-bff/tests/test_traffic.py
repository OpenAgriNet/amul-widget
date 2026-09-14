from __future__ import annotations

import asyncio
import os
import time
from uuid import uuid4

import pytest

from widget_bff.config import Settings
from widget_bff.models import SessionClaims
from widget_bff.traffic import (
    GenerationInProgress,
    MemoryTrafficGuard,
    RateLimitExceeded,
    RedisTrafficGuard,
)


def claims() -> SessionClaims:
    now = int(time.time())
    return SessionClaims(
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


def test_memory_guard_rejects_concurrent_generation_and_releases_lease() -> None:
    async def scenario() -> None:
        guard = MemoryTrafficGuard(Settings(advisory_turn_limit=3))
        session_claims = claims()
        lease = await guard.start_turn(session_claims)

        with pytest.raises(GenerationInProgress):
            await guard.start_turn(session_claims)

        await guard.finish_turn(lease)
        next_lease = await guard.start_turn(session_claims)
        await guard.finish_turn(next_lease)

    asyncio.run(scenario())


def test_memory_guard_enforces_turn_limit() -> None:
    async def scenario() -> None:
        guard = MemoryTrafficGuard(Settings(advisory_turn_limit=1))
        session_claims = claims()
        lease = await guard.start_turn(session_claims)
        await guard.finish_turn(lease)

        with pytest.raises(RateLimitExceeded):
            await guard.start_turn(session_claims)

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.getenv("TEST_REDIS_URL"), reason="Redis integration is opt-in"
)
def test_redis_guard_shares_limits_and_leases_across_instances() -> None:
    async def scenario() -> None:
        settings = Settings(
            redis_url=os.environ["TEST_REDIS_URL"],
            redis_key_prefix=f"widget-ci-{uuid4()}",
            advisory_turn_limit=3,
        )
        first = RedisTrafficGuard(settings)
        second = RedisTrafficGuard(settings)
        session_claims = claims()
        assert await first.ready()

        lease = await first.start_turn(session_claims)
        with pytest.raises(GenerationInProgress):
            await second.start_turn(session_claims)
        await first.finish_turn(lease)

        lease = await second.start_turn(session_claims)
        await second.finish_turn(lease)
        with pytest.raises(RateLimitExceeded):
            await first.start_turn(session_claims)

        await first.close()
        await second.close()

    asyncio.run(scenario())
