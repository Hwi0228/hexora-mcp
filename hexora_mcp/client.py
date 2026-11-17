import httpx

from hexora_mcp.auth_context import auth0_identity


class HexoraClient:
    def __init__(self, base_url: str, token: str, timeout: float = 20):
        self.base_url = base_url.rstrip("/") + "/api/integrations/mcp"
        self.token = token
        self.timeout = timeout

    async def request(self, method: str, path: str, **kwargs):
        if not self.token:
            return {"ok": False, "error": "HEXORA_API_TOKEN is not configured"}
        identity = auth0_identity.get()
        if identity is None:
            return {"ok": False, "error": "An authenticated Auth0 identity is required"}
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "X-HEXORA-Auth0-Sub": identity["sub"],
            "X-HEXORA-Auth0-Email": identity["email"],
            "X-HEXORA-Auth0-Email-Verified": "true",
            "X-HEXORA-Scopes": " ".join(identity["scopes"]),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                response = await http.request(
                    method, self.base_url + path, headers=headers, **kwargs
                )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text[:1000]
            return {
                "ok": False,
                "error": f"HEXORA API HTTP {exc.response.status_code}",
                "detail": detail,
            }
        except httpx.HTTPError as exc:
            return {"ok": False, "error": f"HEXORA API connection failed: {exc}"}
