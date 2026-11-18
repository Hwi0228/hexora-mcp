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

`create_question`은 공개 문제 DB에 즉시 등록합니다. 사용자가 명시적으로 등록을 요청한 경우에만 호출해야 합니다.

## Auth0 인증

MCP 인증 서버는 Auth0이며, HEXORA는 Auth0가 발급한 JWT의 검증된 이메일을 기존 계정과 연결합니다. Auth0에 로그인한 이메일이 HEXORA 기존 계정의 이메일과 일치하고 `email_verified=true`인 경우에만 연결됩니다. 일치하는 기존 계정이 없으면 등록 요청을 거부하며, 임의의 새 계정이나 공용 작성자 계정을 만들지 않습니다.

### Auth0 설정

1. Auth0 Dashboard에서 API를 생성합니다.
   - Name: `HEXORA MCP`
   - Identifier: `https://mcp.hexora.kro.kr/mcp` (아래 `AUTH0_AUDIENCE`와 정확히 일치)
   - Signing Algorithm: `RS256`
2. API Permissions에 `questions:read`, `questions:write`를 추가합니다.
3. API 설정에서 RBAC을 활성화하고 Access Token에 Permissions를 포함합니다.
4. Auth0 Tenant Settings → Advanced에서 **Resource Parameter Compatibility Profile**을 활성화해 RFC 8707 `resource` 요청을 API audience로 처리하도록 합니다.
5. Auth0 Dashboard → Actions → Library에서 Post Login Action을 만들고 다음 코드를 추가한 뒤 Login Flow에 배포합니다.

```js
exports.onExecutePostLogin = async (event, api) => {
  api.accessToken.setCustomClaim("https://hexora.kro.kr/email", event.user.email);
  api.accessToken.setCustomClaim("https://hexora.kro.kr/email_verified", event.user.email_verified === true);
};
```

이 Action은 MCP가 기존 HEXORA 계정을 안전하게 찾는 데 필요한 이메일 및 인증 여부를 API Access Token에 넣습니다. 이메일이 인증되지 않은 계정은 MCP에서 거부됩니다.
6. MCP 연결 클라이언트 등록은 Auth0의 Dynamic Client Registration 또는 CIMD 설정을 사용합니다. Auth0의 Authorization Server metadata가 ChatGPT가 요구하는 등록 방식, PKCE(S256), `none` 또는 `private_key_jwt` token endpoint authentication을 광고하는지 확인합니다.
7. Auth0 API의 third-party application access policy에서 ChatGPT 클라이언트에 필요한 `questions:read` 및 `questions:write` 권한을 허용합니다.

Auth0 Tenant의 기본 API Audience도 위 API Identifier로 설정하면 권장됩니다. API 권한이 발급 토큰의 `scope` 또는 `permissions` claim에 포함되어야 합니다.

### Render 환경 변수

**HEXORA 웹 서비스**
- `HEXORA_MCP_API_TOKEN`: MCP 서비스와 공유하는 서버 간 비밀값

**HEXORA MCP 서비스**
- `HEXORA_API_BASE_URL=https://hexora.kro.kr`
- `HEXORA_API_TOKEN`: HEXORA의 `HEXORA_MCP_API_TOKEN`과 동일한 값
- `MCP_PUBLIC_URL=https://mcp.hexora.kro.kr`
- `MCP_RESOURCE_METADATA_URL=https://mcp.hexora.kro.kr/.well-known/oauth-protected-resource/mcp`
- `AUTH0_DOMAIN`: Auth0 tenant 도메인(예: `tenant.region.auth0.com`)
- `AUTH0_ISSUER`: Auth0 issuer(도메인에 `https://`와 마지막 `/` 포함)
- `AUTH0_AUDIENCE=https://mcp.hexora.kro.kr/mcp`

기존 HEXORA↔MCP 내부 API 비밀값은 유지합니다. `MCP_ACCESS_TOKEN`, 기존 HEXORA OAuth 토큰 introspection 설정은 더 이상 MCP 사용자 인증에 사용하지 않습니다.

### ChatGPT 연결

MCP URL은 `https://mcp.hexora.kro.kr/mcp`입니다. 연결 인증은 OAuth로 설정합니다. 첫 인증에서 Auth0 로그인 및 권한 동의가 진행됩니다.

## 로컬 실행

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
```

`.env.example`을 참고해 환경 변수를 설정한 뒤:

```bash
uvicorn asgi:app --host 0.0.0.0 --port 8000
```

헬스 체크는 `/healthz`, Protected Resource Metadata는 `/.well-known/oauth-protected-resource/mcp`, MCP endpoint는 `/mcp`입니다.

## 성취기준 데이터 범위

현재 HEXORA의 `CURRICULUM_STANDARDS` 데이터에 실제 등록된 성취기준만 반환합니다.

## 테스트

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```
