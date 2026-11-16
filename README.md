# HEXORA MCP

ChatGPT MCP connector for the HEXORA mathematics question bank.

The complete source package, including the MCP server, HEXORA Flask integration patch, Render deployment template, and tests, is provided in `hexora-mcp-source.zip`.

See the ZIP archive for setup instructions in its `README.md`. Do not commit secrets; configure `HEXORA_API_TOKEN`, `MCP_ACCESS_TOKEN`, and HEXORA's `HEXORA_MCP_API_TOKEN` / `HEXORA_MCP_SERVICE_USER_UUID` as deployment environment variables.

**Status:** source scaffold uploaded; HEXORA integration patch and Render service still need deployment and live verification.