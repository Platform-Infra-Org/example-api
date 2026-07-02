import os

# 32+ bytes to avoid PyJWT's short-key warning.
HS256_SECRET = "test-secret-test-secret-test-secret"

# The app's per-module config singletons and the library's auth verifier are built at
# import / app-creation time, so the required settings must exist in the environment
# before `app.main` is imported below. AUTH_ENABLED + AUTH_HS256_SECRET turn on the
# global AuthMiddleware (HS256 mode) so the whole app is inbound-protected under test.
_BASE_ENV = {
    "ARGOCD_URL": "https://argo.test",
    "ARGOCD_TOKEN": "x",
    "VAULT_URL": "https://vault.test",
    "VAULT_TOKEN": "x",
    "TEAM_NAME": "test-team",
    "CLUSTERS": '["dev"]',
    "HAPROXY_VALUES_REPO_URL": "https://git.test",
    "HAPROXY_VALUES_REPO_ACCESS_TOKEN": "x",
    "HAPROXY_VALUES_REPO_EMAIL": "svc@test",
    "HAPROXY_REPO_PROJECT_KEY": "dev",
    "HAPROXY_VALUES_REPO_SLUG": "haproxy-values",
    "HAPROXY_VALUES_REPO_SSH_KEY_PATH": "/tmp/key",
    "AUTH_ENABLED": "true",
    "AUTH_HS256_SECRET": HS256_SECRET,
}
for _k, _v in _BASE_ENV.items():
    os.environ.setdefault(_k, _v)

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from tashtiot_apis_library.fastapi_template.utils import settings
from tashtiot_apis_library.fastapi_template._internal.security import sso as sso_mod


@pytest.fixture
def app():
    from app.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def outbound_sso(monkeypatch):
    """Configure outbound SSO client_credentials and reset the token cache."""
    monkeypatch.setattr(settings, "AUTH_SSO_TOKEN_URL", "https://idp.test/token")
    monkeypatch.setattr(settings, "AUTH_SSO_CLIENT_ID", "svc")
    monkeypatch.setattr(settings, "AUTH_SSO_CLIENT_SECRET", "s3cret")
    monkeypatch.setattr(settings, "AUTH_SSO_SCOPE", None)
    monkeypatch.setattr(settings, "AUTH_SSO_AUDIENCE", None)
    monkeypatch.setattr(settings, "AUTH_SSO_AUTH_STYLE", "post")
    monkeypatch.setattr(settings, "AUTH_SSO_VERIFY_SSL", False)
    sso_mod._token_client_cache.clear()
    yield
    sso_mod._token_client_cache.clear()


@pytest.fixture
def make_token():
    def _make(secret=HS256_SECRET, **claims):
        payload = {"sub": "svc-demo", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
        payload.update(claims)
        return jwt.encode(payload, secret, algorithm="HS256")

    return _make
