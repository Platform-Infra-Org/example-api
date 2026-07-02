from typing import Any, Dict, Optional

from pydantic import BaseModel


class WhoAmI(BaseModel):
    """The verified caller identity, derived from the inbound JWT claims."""

    subject: str
    claims: Dict[str, Any]


class DownstreamResult(BaseModel):
    """Outcome of the outbound SSO-authenticated downstream call.

    status is one of: "ok" (2xx/3xx), "downstream_error" (the downstream returned
    4xx/5xx), or "auth_failed" (no AUTH_SSO_* configured, so no token could be minted).
    """

    status: str
    status_code: Optional[int] = None
    data: Optional[Any] = None
