from contextvars import ContextVar

oauth_access_token: ContextVar[str] = ContextVar("hexora_oauth_access_token", default="")
