# HEXORA MCP

ChatGPT-compatible MCP server for the HEXORA mathematics question bank.

## Tools
- `search_questions`, `get_question`, `get_standards`
- `validate_question`, `create_question`
- `health_check`

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
copy .env.example .env
python server.py
```

HTTP transport is Streamable HTTP at `/mcp`; set `MCP_TRANSPORT=stdio` for local stdio use.

## Deployment
Deploy this service to an HTTPS host supporting Streamable HTTP. Configure `HEXORA_API_BASE_URL`, `HEXORA_API_TOKEN`, and a separate `MCP_ACCESS_TOKEN`. Apply `hexora_patch/mcp_api.py` to the HEXORA Flask application and configure `HEXORA_MCP_API_TOKEN` and `HEXORA_MCP_SERVICE_USER_UUID` there.

Creation writes to the existing question table after validation. It is **not** a draft workflow: only call `create_question` when the user explicitly asks to register a question. The standards endpoint must be connected to the actual curriculum data source before use.

The Flask patch must be reviewed against the exact deployed HEXORA revision before applying. Live DB compatibility and deployment have not yet been verified. Never commit secrets.
