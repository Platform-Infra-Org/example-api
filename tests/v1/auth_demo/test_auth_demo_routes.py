import httpx
import pytest
import respx

from tashtiot_apis_library.fastapi_template._internal.security import sso as sso_mod

from app.v1.auth_demo.conf import config
from app.v1.auth_demo.operations import call_downstream_with_sso

PREFIX = config.API_PREFIX


# --------------------------------------------------------------------------- #
# Inbound auth — the global AuthMiddleware protects every route (AUTH_ENABLED +
# AUTH_HS256_SECRET are set in conftest). Exercised end-to-end via TestClient.
# --------------------------------------------------------------------------- #


def test_whoami_requires_token(client):
    assert client.get(f"{PREFIX}/whoami").status_code == 401


def test_whoami_rejects_bad_token(client):
    r = client.get(f"{PREFIX}/whoami", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_whoami_accepts_valid_token(client, make_token):
    r = client.get(f"{PREFIX}/whoami", headers={"Authorization": f"Bearer {make_token()}"})
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "svc-demo"
    assert body["claims"]["sub"] == "svc-demo"


def test_downstream_requires_inbound_token(client):
    # Auth is now global, so the downstream route is protected too.
    assert client.get(f"{PREFIX}/downstream").status_code == 401


def test_downstream_runs_with_valid_token(client, make_token):
    # With a valid bearer the route runs; AUTH_SSO_* is unset here, so the outbound
    # call is gracefully reported as auth_failed (HTTP 200 with a result body).
    r = client.get(f"{PREFIX}/downstream", headers={"Authorization": f"Bearer {make_token()}"})
    assert r.status_code == 200
    assert r.json()["status"] == "auth_failed"


# --------------------------------------------------------------------------- #
# Outbound SSO — tested at the operation level with the IdP token endpoint and
# the downstream service mocked (respx). Avoids TestClient/respx interplay.
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@respx.mock
async def test_downstream_attaches_sso_bearer(outbound_sso):
    respx.post("https://idp.test/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 3600})
    )
    downstream = respx.get(f"{config.DOWNSTREAM_API_URL}{config.DOWNSTREAM_ENDPOINT}").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )

    result = await call_downstream_with_sso()

    assert result.status == "ok"
    assert result.status_code == 200
    assert result.data == {"ok": True}
    assert downstream.calls.last.request.headers["Authorization"] == "Bearer tok-1"


@pytest.mark.asyncio
@respx.mock
async def test_downstream_reports_downstream_error(outbound_sso):
    respx.post("https://idp.test/token").mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1", "expires_in": 3600})
    )
    respx.get(f"{config.DOWNSTREAM_API_URL}{config.DOWNSTREAM_ENDPOINT}").mock(
        return_value=httpx.Response(503, json={"err": "down"})
    )

    result = await call_downstream_with_sso()

    assert result.status == "downstream_error"
    assert result.status_code == 503


@pytest.mark.asyncio
async def test_downstream_auth_failure_is_graceful():
    # No AUTH_SSO_* configured -> AuthConfigError is caught and surfaced cleanly.
    sso_mod._token_client_cache.clear()
    result = await call_downstream_with_sso()
    assert result.status == "auth_failed"
    assert result.status_code is None
