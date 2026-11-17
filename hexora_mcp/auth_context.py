from contextvars import ContextVar
from typing import TypedDict


class Auth0Identity(TypedDict):
    sub: str
    email: str
    email_verified: bool
    scopes: list[str]


auth0_identity: ContextVar[Auth0Identity | None] = ContextVar(
    "hexora_auth0_identity",
    default=None,
)
