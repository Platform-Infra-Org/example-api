from fastapi import APIRouter, Depends
from tashtiot_apis_library.fastapi_template.auth import get_current_claims

from .conf import config
from .operations import call_downstream_with_sso
from .schemas import DownstreamResult, WhoAmI


def get_v1_auth_demo_router() -> APIRouter:
    router = APIRouter(prefix=config.API_PREFIX, tags=config.API_TAGS)

    @router.get(
        "/whoami",
        response_model=WhoAmI,
        summary="Return the verified caller identity (inbound SSO)",
    )
    def whoami(claims: dict = Depends(get_current_claims)) -> WhoAmI:
        # get_current_claims reads request.state.user, which the global AuthMiddleware
        # sets after verifying the bearer. It 401s when there's no verified identity
        # (no token, or auth disabled), so /whoami always requires an authenticated caller.
        return WhoAmI(subject=claims["sub"], claims=claims)

    @router.get(
        "/downstream",
        response_model=DownstreamResult,
        summary="Call a downstream API with an SSO bearer (outbound SSO client)",
    )
    async def downstream() -> DownstreamResult:
        return await call_downstream_with_sso()

    return router
