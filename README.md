# HEXORA MCP

HEXORA의 공개 수학 문제은행을 ChatGPT 등 MCP 클라이언트에서 사용하는 원격 MCP 서버입니다.

## 제공 도구

| 도구 | 기능 | 쓰기 여부 |
|---|---|---|
| `health_check` | HEXORA API 연결 확인 | 읽기 |
| `search_questions` | 문항 검색 및 필터링 | 읽기 |
| `get_question` | 6자리 Base36 문항 상세 조회 | 읽기 |
| `get_standards` | 등록된 성취기준 검색 | 읽기 |
| `validate_question` | 저장 전 문항 검증 | 읽기 |
| `create_question` | 공개 문제 DB에 문항 등록 | 쓰기 |

`create_question`은 임시 저장이 아니라 공개 문제 DB에 즉시 등록합니다. 사용자가 명시적으로 등록을 요청한 경우에만 호출해야 합니다. 변형 기준 문항 번호를 제공하면 문제 계보 링크도 함께 생성합니다.

## HEXORA API 연동 및 OAuth 2.1

HEXORA 로그인 계정을 사용하는 OAuth 2.1 Authorization Code + PKCE(S256) 인증을 지원합니다. MCP 클라이언트 사용자가 자신의 HEXORA 계정으로 로그인하고 권한을 승인하면, 각 요청은 해당 사용자 권한으로 실행됩니다.

HEXORA Render 환경 변수:
- `HEXORA_MCP_API_TOKEN`: MCP 서버와 HEXORA API 사이의 비공개 서버 간 인증 토큰
- `MCP_PUBLIC_URL`: 공개 MCP URL. 기본값은 `https://hexora-mcp.onrender.com`

MCP Render 환경 변수:
- `HEXORA_API_BASE_URL=https://hexora.kro.kr`
- `HEXORA_API_TOKEN`: HEXORA의 `HEXORA_MCP_API_TOKEN`과 동일한 비밀값
- `MCP_PUBLIC_URL=https://hexora-mcp.onrender.com` (커스텀 도메인 연결 후 해당 주소로 변경 가능)

OAuth 엔드포인트:
- Authorization Server Metadata: `https://hexora.kro.kr/.well-known/oauth-authorization-server`
- Authorization: `https://hexora.kro.kr/oauth/authorize`
- Token: `https://hexora.kro.kr/oauth/token`
- Dynamic Client Registration: `https://hexora.kro.kr/oauth/register`
- Protected Resource Metadata: MCP 서버의 `/.well-known/oauth-protected-resource/mcp`
- MCP endpoint: `/mcp`

지원 범위:
- Authorization Code + PKCE(S256)
- Dynamic Client Registration
- Access token(1시간) 및 refresh token(30일) 회전
- Token revocation 및 내부 token introspection
- `questions:read`, `questions:write` 권한 분리
- 문항 등록 시 OAuth로 인증한 HEXORA 계정을 작성자로 사용

ChatGPT 연결 시 서버 URL은 `https://hexora-mcp.onrender.com/mcp`입니다. 인증 방식은 OAuth를 선택합니다. 사용자는 HEXORA 로그인 및 권한 승인 화면에서 연결하면 되며, 개인별 PowerShell 환경 변수나 공용 Bearer 토큰을 입력할 필요가 없습니다.

`create_question`은 공개 문제 DB에 즉시 등록합니다. 사용자가 명시적으로 등록을 요청한 경우에만 호출해야 합니다.

## 로컬 실행

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
```

환경 변수:
```env
HEXORA_API_BASE_URL=https://hexora.kro.kr
HEXORA_API_TOKEN=<HEXORA_MCP_API_TOKEN과 동일한 값>
MCP_PUBLIC_URL=http://localhost:8000
```

```bash
uvicorn asgi:app --host 0.0.0.0 --port 8000
```

## 성취기준 데이터 범위

현재 HEXORA의 `CURRICULUM_STANDARDS` 데이터에는 `2015 개정 교육과정`의 일부 수학Ⅱ 성취기준이 포함되어 있습니다. API는 실제 등록된 데이터만 반환하며, 데이터가 없는 교육과정에 대해 성취기준을 만들어 내지 않습니다. `2022 개정 교육과정` 자료는 HEXORA의 원본 데이터가 추가된 뒤 검색할 수 있습니다.

## 테스트

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```
