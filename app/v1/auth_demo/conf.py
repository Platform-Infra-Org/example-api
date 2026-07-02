# ─────────────────────────────────────────────────────────────────────────────
#   Settings for the Auth Demo v1 API (inbound JWT + outbound SSO client).
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthDemoSettings(BaseSettings):
    """Config for the auth_demo module.

    Inbound verification material (AUTH_HS256_SECRET / AUTH_JWKS_URL / …) and the
    outbound SSO credentials (AUTH_SSO_*) are NOT declared here — the library reads
    those from the environment itself. This module only needs its own routing prefix
    and the downstream target for the outbound-SSO example.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    API_PREFIX: str = Field(
        description="Root path under which the auth demo API is served",
        default="/api/example/v1/auth_demo",
    )

    API_TAGS: List[str] = Field(
        description="Tags used for OpenAPI documentation grouping",
        default_factory=lambda: ["v1 - Auth Demo"],
    )

    DOWNSTREAM_API_URL: str = Field(
        description="Base URL of the downstream service called with an SSO bearer",
        default="https://downstream.example.com",
    )

    DOWNSTREAM_ENDPOINT: str = Field(
        description="Path on the downstream service to call",
        default="/protected",
    )


config = AuthDemoSettings()
