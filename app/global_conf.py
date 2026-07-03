from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class ExampleStaticSettings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    API_TITLE: str = Field(
        description="API title for the swagger", 
        default="Domain Services API - Example API",
    )

    AWX_URL: str = Field(
        description="AWX base URL",
        default="https://web.awx.app.com/",
    )

    AWX_TOKEN: str = Field(
        description="AWX token for the AWX client",
        default="sheker123",
    )

    CHAT_API_URL: str = Field(
        description="CHAT api url",
        default="https://sendman.com",
    )

    CHAT_API_TOKEN: str = Field(
        description="CHAT API token",
        default="sheker_token",
    )
    
    # Shared service config
    ARGOCD_URL: str = Field(description="The service owner's ArgoCD URL.")
    ARGOCD_TOKEN: str = Field(description="The service owner's ArgoCD token.")
    APPLICATION_SET_TIMEOUT: Optional[int] = Field(default=60, description="Seconds to wait for appset operations.")

    VAULT_URL: str = Field(description="Base URL for HashiCorp Vault")
    VAULT_TOKEN: str = Field(description="Token used to authenticate to Vault.")

    TEAM_NAME: str = Field(description="Team name used as Vault mount path prefix.")

    # Remote Config provider (optional). When CONFIG_API_URL is set, create_app wires
    # the library's enable_remote_config_api against that upstream. The outbound-auth
    # knobs (CONFIG_REMOTE_*) are read by the library's ConfigRemoteSettings from env.
    CONFIG_API_URL: Optional[str] = Field(
        default=None,
        description="Base URL of the upstream Config API. When set, the Remote Config provider is wired.",
    )
    CONFIG_API_REMOTE_PREFIX: str = Field(
        default="/api/v1",
        description="Route prefix under which the upstream Config API serves /config, /naming, /projects.",
    )
    
    CONFIG_POLL_INTERVAL_SECONDS: int = Field(
        default=5,
        description="Interval for the background loop that syncs the live allowlists (from the upstream) and invalidates the cached OpenAPI schema.",
    )

    CONFIG_CACHE_TTL_SECONDS: int = Field(
        default=60,
        description="TTL (seconds) for the in-memory cache of upstream config/naming/projects responses.",
    )

    CONFIG_SERVE_STALE_ON_ERROR: bool = Field(
        default=False,
        description="When the upstream is down/5xx, serve the last good (expired) cached response instead of 502.",
    )

global_config = ExampleStaticSettings()