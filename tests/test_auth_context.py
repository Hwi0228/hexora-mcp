from hexora_mcp.auth_context import auth0_identity


def test_auth0_identity_context_defaults_to_none():
    assert auth0_identity.get() is None


def test_auth0_identity_context_is_request_scoped():
    identity = {
        "sub": "auth0|test-user",
        "email": "test@example.com",
        "email_verified": True,
        "scopes": ["questions:read", "questions:write"],
    }
    token = auth0_identity.set(identity)
    try:
        assert auth0_identity.get() == identity
    finally:
        auth0_identity.reset(token)
