import json
import httpx

from hexora_mcp.auth_context import oauth_access_token
from server import mcp

HEXORA_BASE = os.getenv("HEXORA_API_BASE_URL", "https://hexora.kro.kr").rstrip("/")
HEXORA_TOKEN = os.getenv("HEXORA_API_TOKEN", "")
RESOURCE_METADATA = os.getenv(
    "MCP_RESOURCE_METADATA_URL",
    "https://mcp.hexora.kro.kr/.well-known/oauth-protected-resource/mcp",
)
inner = mcp.streamable_http_app()


class OAuthResourceMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if path == "/healthz":
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"ok":true}'})
            return
        if path != "/mcp":
            if path == "/.well-known/oauth-protected-resource/mcp":
                body = json.dumps({
                    "resource": "https://mcp.hexora.kro.kr/mcp",
                    "authorization_servers": ["https://hexora.kro.kr"],
                    "bearer_methods_supported": ["header"],
                    "scopes_supported": ["questions:read", "questions:write"],
                }).encode()
                await send({"type": "http.response.start", "status": 200,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
                return
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        token = authorization[7:].strip() if authorization.startswith("Bearer ") else ""
        if not token or not HEXORA_TOKEN:
            await self.unauthorized(send)
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    HEXORA_BASE + "/oauth/introspect",
                    headers={"Authorization": f"Bearer {HEXORA_TOKEN}"},
                    data={"token": token},
                )
            data = response.json() if response.status_code == 200 else {}
        except (httpx.HTTPError, ValueError):
            data = {}
        if not data.get("active"):
            await self.unauthorized(send)
            return

        marker = oauth_access_token.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            oauth_access_token.reset(marker)

    async def unauthorized(self, send):
        challenge = (
            'Bearer resource_metadata="' + RESOURCE_METADATA
            + '", scope="questions:read questions:write"'
        )
        body = json.dumps({"error": "unauthorized", "error_description": "A valid HEXORA OAuth access token is required."}).encode()
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


app = OAuthResourceMiddleware(inner)
