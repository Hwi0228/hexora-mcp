import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from hexora_mcp.client import HexoraClient
from hexora_mcp.schemas import QuestionInput

load_dotenv()
mcp = FastMCP("HEXORA", instructions=(
    "HEXORA mathematics question bank. Search for duplicates and validate before creating. "
    "Creation writes to the public question bank; only create when explicitly requested."
), host=os.getenv("MCP_HOST", "0.0.0.0"), port=int(os.getenv("MCP_PORT", "8000")))
api = HexoraClient(os.getenv("HEXORA_API_BASE_URL", "https://hexora.kro.kr"),
                   os.getenv("HEXORA_API_TOKEN", ""),
                   float(os.getenv("HEXORA_REQUEST_TIMEOUT", "20")))

@mcp.tool()
async def health_check() -> dict:
    """Check connectivity to HEXORA."""
    return await api.request("GET", "/health")

@mcp.tool()
async def search_questions(query: str = "", subject: str = "", grade: str = "",
                           achievement_standard: str = "", difficulty: str = "",
                           limit: int = 10) -> dict:
    """Search the question bank; search before creating similar questions."""
    if not 1 <= limit <= 50:
        return {"ok": False, "error": "limit must be between 1 and 50"}
    return await api.request("GET", "/questions", params=locals())

@mcp.tool()
async def get_question(code: str) -> dict:
    """Get a question by its six-character Base36 code."""
    code = code.strip().upper()
    if len(code) != 6 or any(c not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" for c in code):
        return {"ok": False, "error": "문항 코드는 6자리 Base36 형식이어야 합니다."}
    return await api.request("GET", f"/questions/{code}")

@mcp.tool()
async def get_standards(query: str = "", curriculum: str = "2022 개정 교육과정",
                        subject: str = "", grade: str = "", limit: int = 30) -> dict:
    """Search the configured achievement-standard source."""
    if not 1 <= limit <= 100:
        return {"ok": False, "error": "limit must be between 1 and 100"}
    return await api.request("GET", "/standards", params={
        "query": query, "curriculum": curriculum, "subject": subject, "grade": grade, "limit": limit
    })

@mcp.tool()
async def validate_question(question: dict) -> dict:
    """Validate question fields without saving."""
    try:
        data = QuestionInput.model_validate(question).model_dump()
    except Exception as exc:
        return {"ok": False, "valid": False, "errors": [str(exc)]}
    return await api.request("POST", "/questions/validate", json=data)

@mcp.tool()
async def create_question(question: dict) -> dict:
    """Create a validated question in HEXORA's public question bank."""
    try:
        data = QuestionInput.model_validate(question).model_dump()
    except Exception as exc:
        return {"ok": False, "created": False, "errors": [str(exc)]}
    checked = await api.request("POST", "/questions/validate", json=data)
    if not checked.get("valid", False):
        return {"ok": False, "created": False, "validation": checked}
    return await api.request("POST", "/questions", json={"question": data})

if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    mcp.run(transport="stdio" if transport == "stdio" else "streamable-http")
