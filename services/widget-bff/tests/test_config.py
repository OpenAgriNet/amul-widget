import pytest
from pydantic import ValidationError

from widget_bff.config import DEVELOPMENT_JWT_SECRET, Settings


def test_production_rejects_development_signing_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", jwt_secret=DEVELOPMENT_JWT_SECRET)


def test_production_requires_redis() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            jwt_secret="production-secret-with-enough-entropy",
        )


def test_short_signing_secret_is_rejected_in_every_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="test", jwt_secret="too-short")


def test_empty_upstream_url_is_treated_as_unconfigured() -> None:
    settings = Settings(amul_api_base_url="")

    assert settings.amul_api_base_url is None


def test_empty_redis_url_is_treated_as_unconfigured() -> None:
    settings = Settings(redis_url="")

    assert settings.redis_url is None
