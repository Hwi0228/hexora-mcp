# Apply to HEXORA

Copy `mcp_api.py` to the Flask project root and register the blueprint inside the app factory:

```python
from mcp_api import mcp_api
app.register_blueprint(mcp_api)
```

Configure `HEXORA_MCP_API_TOKEN` and `HEXORA_MCP_SERVICE_USER_UUID` on the HEXORA service. The UUID must belong to an existing service-author account. Configure the same API token as `HEXORA_API_TOKEN` on this MCP service.

**Review the patch against the exact deployed HEXORA branch before deploying.** The integration patch uses existing repository helpers and schema assumptions that need live verification.
