from tashtiot_apis_library.fastapi_template.errors import AuthConfigError
from tashtiot_apis_library.fastapi_template.security import sso_authenticated_api

from .conf import config
from .schemas import DownstreamResult


async def call_downstream_with_sso() -> DownstreamResult:
    """Call the downstream API with an OAuth2 client_credentials bearer.

    `sso_authenticated_api` returns a BaseAPI async client that mints and refreshes
    the token from the AUTH_SSO_* environment settings and attaches it to every
    request. If those settings are absent, building the client raises AuthConfigError,
    which we surface as a clean "auth_failed" result rather than a 500.
    """
    try:
        async with sso_authenticated_api(config.DOWNSTREAM_API_URL) as client:
            response = await client.get(config.DOWNSTREAM_ENDPOINT)
    except AuthConfigError:
        return DownstreamResult(status="auth_failed", status_code=None, data=None)

    try:
        data = response.json()
    except ValueError:
        data = None

    status = "ok" if response.status_code < 400 else "downstream_error"
    return DownstreamResult(status=status, status_code=response.status_code, data=data)
