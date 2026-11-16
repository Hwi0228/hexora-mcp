import os

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from hexora_mcp.client import HexoraClient
from hexora_mcp.schemas import QuestionInput

load_dotenv()
mcp = FastMCP(
    "HEXORA",
    instructions=(
        "HEXORA shared mathematics question bank. Search for duplicates and validate "
        "before creating. create_question writes permanently to the public question bank; "
        "never call it unless the user explicitly asks to register the question."
    ),
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)
api = HexoraClient(
    os.getenv("HEXORA_API_BASE_URL", "https://hexora.kro.kr"),
    os.getenv("HEXORA_API_TOKEN", ""),
    float(os.getenv("HEXORA_REQUEST_TIMEOUT", "20")),
)


@mcp.tool()
async def health_check() -> dict:
    """Check whether the authenticated HEXORA API is reachable."""
    return await api.request("GET", "/health")


@mcp.tool()
async def search_questions(
    query: str = "",
    subject: str = "",
    grade: str = "",
    course: str = "",
    achievement_standard: str = "",
    difficulty: str = "",
    limit: int = 10,
) -> dict:
    """Search public HEXORA questions. Search before creating to avoid duplicates."""
    if not 1 <= limit <= 50:
        return {"ok": False, "error": "limit must be between 1 and 50"}
    return await api.request(
        "GET",
        "/questions",
        params={
            "query": query,
            "subject": subject,
            "grade": grade,
            "course": course,
            "achievement_standard": achievement_standard,
            "difficulty": difficulty,
            "limit": limit,
        },
    )


@mcp.tool()
async def get_question(code: str) -> dict:
    """Get a question by its six-character Base36 code."""
    code = code.strip().upper()
    if len(code) != 6 or any(char not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" for char in code):
        return {"ok": False, "error": "문항 코드는 6자리 Base36 형식이어야 합니다."}
    return await api.request("GET", f"/questions/{code}")


@mcp.tool()
async def get_standards(
    query: str = "",
    curriculum: str = "2015 개정 교육과정",
    course: str = "",
    limit: int = 30,
) -> dict:
    """Search the achievement standards actually configured in HEXORA."""
    if not 1 <= limit <= 100:
        return {"ok": False, "error": "limit must be between 1 and 100"}
    return await api.request(
        "GET",
        "/standards",
        params={
            "query": query,
            "curriculum": curriculum,
            "course": course,
            "limit": limit,
        },
    )


@mcp.tool()
async def validate_question(question: dict) -> dict:
    """Validate a proposed question without saving it to the public bank."""
    try:
        data = QuestionInput.model_validate(question).model_dump()
    except ValidationError as exc:
        return {"ok": False, "valid": False, "errors": [str(exc)]}
    return await api.request("POST", "/questions/validate", json=data)


@mcp.tool()
async def create_question(question: dict) -> dict:
    """Register a question in the public bank. Use only after explicit user instruction."""
    try:
        data = QuestionInput.model_validate(question).model_dump()
    except ValidationError as exc:
        return {"ok": False, "created": False, "errors": [str(exc)]}
    checked = await api.request("POST", "/questions/validate", json=data)
    if not checked.get("valid", False):
        return {"ok": False, "created": False, "validation": checked}
    return await api.request("POST", "/questions", json={"question": data})


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    mcp.run(transport="stdio" if transport == "stdio" else "streamable-http")
