from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_JWT_SECRET = "development-only-change-before-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WIDGET_",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    jwt_secret: SecretStr = SecretStr(DEVELOPMENT_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "https://widget.amulai.in"
    jwt_audience: str = "amul-widget-bff"
    anonymous_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    amul_api_base_url: AnyHttpUrl | None = None
    upstream_timeout_seconds: float = Field(default=90.0, ge=1.0, le=300.0)
    hosts_json: str | None = None

    @field_validator("amul_api_base_url", mode="before")
    @classmethod
    def treat_empty_upstream_url_as_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_development_secret_in_production(self) -> Settings:
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise ValueError("WIDGET_JWT_SECRET must contain at least 32 characters")
        if (
            self.environment == "production"
            and self.jwt_secret.get_secret_value() == DEVELOPMENT_JWT_SECRET
        ):
            raise ValueError("WIDGET_JWT_SECRET must be set in production")
        return self
