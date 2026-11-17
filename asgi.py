import asyncio
import json
import os

import jwt
from dotenv import load_dotenv
from jwt import PyJWKClient

from hexora_mcp.auth_context import auth0_identity
from server import mcp

load_dotenv()

HEXORA_BASE = os.getenv("HEXORA_API_BASE_URL", "https://hexora.kro.kr").rstrip("/")
HEXORA_TOKEN = os.getenv("HEXORA_API_TOKEN", "")
MCP_PUBLIC_URL = os.getenv("MCP_PUBLIC_URL", "https://mcp.hexora.kro.kr").rstrip("/")
RESOURCE_URL = MCP_PUBLIC_URL + "/mcp"
RESOURCE_METADATA = os.getenv(
    "MCP_RESOURCE_METADATA_URL",
    MCP_PUBLIC_URL + "/.well-known/oauth-protected-resource/mcp",
)
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "").strip().removeprefix("https://").removeprefix("http://").rstrip("/")
_AUTH0_ISSUER_RAW = os.getenv("AUTH0_ISSUER", f"https://{AUTH0_DOMAIN}/" if AUTH0_DOMAIN else "").strip()
AUTH0_ISSUER = _AUTH0_ISSUER_RAW.rstrip("/") + "/" if _AUTH0_ISSUER_RAW else ""
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", RESOURCE_URL).strip()
AUTH0_EMAIL_CLAIM = os.getenv("AUTH0_EMAIL_CLAIM", "https://hexora.kro.kr/email")
AUTH0_EMAIL_VERIFIED_CLAIM = os.getenv("AUTH0_EMAIL_VERIFIED_CLAIM", "https://hexora.kro.kr/email_verified")
AUTH0_JWKS_URL = os.getenv("AUTH0_JWKS_URL", f"{AUTH0_ISSUER}.well-known/jwks.json" if AUTH0_ISSUER else "")
JWKS_CLIENT = PyJWKClient(AUTH0_JWKS_URL, cache_jwk_set=True) if AUTH0_JWKS_URL else None

inner = mcp.streamable_http_app()


def _verify_auth0_token(token: str) -> dict:
    if not AUTH0_ISSUER or not AUTH0_AUDIENCE or JWKS_CLIENT is None:
        raise RuntimeError("Auth0 is not configured")
    signing_key = JWKS_CLIENT.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=AUTH0_AUDIENCE,
        issuer=AUTH0_ISSUER,
        options={"require": ["exp", "iat", "sub"]},
    )
    email = claims.get(AUTH0_EMAIL_CLAIM)
    email_verified = claims.get(AUTH0_EMAIL_VERIFIED_CLAIM)
    if not isinstance(email, str) or not email.strip() or email_verified is not True:
        raise jwt.InvalidTokenError("A verified email address is required")
    scopes = set(str(claims.get("scope", "")).split())
    permissions = claims.get("permissions", [])
    if isinstance(permissions, list):
        scopes.update(str(value) for value in permissions)
    return {
        "sub": str(claims["sub"]),
        "email": email.strip().lower(),
        "email_verified": True,
        "scopes": sorted(scopes),
    }


class Auth0ResourceMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/healthz":
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            })
            await send({"type": "http.response.body", "body": b'{"ok":true}'})
            return
        if path == "/.well-known/oauth-protected-resource/mcp":
            body = json.dumps({
                "resource": RESOURCE_URL,
                "authorization_servers": [AUTH0_ISSUER] if AUTH0_ISSUER else [],
                "bearer_methods_supported": ["header"],
                "scopes_supported": ["openid", "email", "profile", "questions:read", "questions:write"],
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json"), (b"cache-control", b"public, max-age=300")],
            })
            await send({"type": "http.response.body", "body": body})
            return
        if path != "/mcp":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        token = authorization[7:].strip() if authorization.startswith("Bearer ") else ""
        if not token:
            await self.unauthorized(send)
            return
        try:
            identity = await asyncio.to_thread(_verify_auth0_token, token)
        except (jwt.PyJWTError, ValueError, RuntimeError):
            await self.unauthorized(send)
            return

        marker = auth0_identity.set(identity)
        try:
            await self.app(scope, receive, send)
        finally:
            auth0_identity.reset(marker)

    async def unauthorized(self, send):
        challenge = (
            'Bearer resource_metadata="' + RESOURCE_METADATA
            + '", scope="questions:read questions:write"'
        )
        body = json.dumps({
            "error": "unauthorized",
            "error_description": "A valid Auth0 access token for the HEXORA API is required.",
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", challenge.encode("ascii")),
                (b"cache-control", b"no-store"),
            ],
        })
        await send({"type": "http.response.body", "body": body})


app = Auth0ResourceMiddleware(inner)
