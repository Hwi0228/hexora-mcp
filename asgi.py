import hmac
import json
import os

from server import mcp

token = os.getenv("MCP_ACCESS_TOKEN", "")
if not token:
    raise RuntimeError("MCP_ACCESS_TOKEN must be configured")
inner = mcp.streamable_http_app()

class AuthMiddleware:
    def __init__(self, app): self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope.get("path") == "/mcp":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode("latin-1")
            supplied = auth[7:] if auth.startswith("Bearer ") else ""
            if not supplied or not hmac.compare_digest(token, supplied):
                body = json.dumps({"error": "Unauthorized"}).encode()
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": body})
                return
        if scope["type"] == "http" and scope.get("path") == "/healthz":
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"ok":true}'})
            return
        await self.app(scope, receive, send)

app = AuthMiddleware(inner)
