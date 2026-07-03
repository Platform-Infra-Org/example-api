"""Hermetic test environment — shadow any developer `.env`.

pydantic-settings gives `os.environ` precedence over the `.env` file, so force-setting
these optional AUTH_*/CONFIG_* knobs to empty here guarantees a local `.env` cannot change
test outcomes by:
  - enabling the Remote Config provider (`CONFIG_API_URL`), which would make the DNS routes
    call a real upstream instead of using the static conf fallback;
  - adding a second inbound-auth material (`AUTH_JWKS_URL` / `AUTH_PUBLIC_KEY_*`), which makes
    `_select_mode` ambiguous and fails app creation — the suites configure HS256 only;
  - preconfiguring outbound SSO (`AUTH_SSO_*`), which the auth-failure test relies on being absent.

Each module's own conftest still sets the base connector + HS256 values it needs (those keys
aren't shadowed here). This file is imported before any app module, so the shadowing lands
before the settings singletons are constructed.
"""
import os

_SHADOW_EMPTY = (
    # Remote Config provider stays off.
    "CONFIG_API_URL",
    # Keep HS256 (set per-module) the only inbound material.
    "AUTH_JWKS_URL",
    "AUTH_OIDC_ISSUER",
    "AUTH_PUBLIC_KEY_PEM",
    "AUTH_PUBLIC_KEY_PATH",
    "AUTH_AUDIENCE",
    "AUTH_ISSUER",
    # No preconfigured outbound SSO.
    "AUTH_SSO_TOKEN_URL",
    "AUTH_SSO_CLIENT_ID",
    "AUTH_SSO_CLIENT_SECRET",
    "AUTH_SSO_SCOPE",
    "AUTH_SSO_AUDIENCE",
    # Provider outbound-auth knobs (unused while the provider is off).
    "CONFIG_REMOTE_AUTH_METHOD",
    "CONFIG_REMOTE_BEARER_TOKEN",
    "CONFIG_REMOTE_SSO_TOKEN_URL",
    "CONFIG_REMOTE_SSO_CLIENT_ID",
    "CONFIG_REMOTE_SSO_CLIENT_SECRET",
)
for _key in _SHADOW_EMPTY:
    os.environ[_key] = ""
