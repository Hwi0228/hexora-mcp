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

## HEXORA API 연동

HEXORA 저장소의 `dev` 브랜치에 API 브리지가 등록되어 있어야 합니다. 해당 브리지는 기존 Flask 인증 훅과 분리된 Bearer 토큰 인증을 사용하며, 기존 `questions` 테이블과 문항 수정 이력 테이블을 그대로 사용합니다.

HEXORA 배포 환경 변수:

- `HEXORA_MCP_API_TOKEN`: MCP 서버가 호출할 내부 API 토큰
- `HEXORA_MCP_SERVICE_USER_UUID`: MCP 등록 문항의 작성자 계정 UUID

HEXORA Render Shell에서 서비스 작성자 계정을 한 번 생성합니다.

```bash
flask --app app create-mcp-service-user
```

출력된 UUID를 `HEXORA_MCP_SERVICE_USER_UUID`에 등록합니다. 이 계정은 일반 로그인용이 아니며, 임의 비밀번호 해시를 사용합니다.

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
MCP_ACCESS_TOKEN=<ChatGPT 연결용 별도 Bearer 토큰>
```

```bash
uvicorn asgi:app --host 0.0.0.0 --port 8000
```

MCP endpoint는 `/mcp`, 헬스 체크는 `/healthz`입니다. `/mcp`는 `MCP_ACCESS_TOKEN` Bearer 인증을 요구합니다.

## Render 배포

`render.yaml`은 무료 웹 서비스 구성으로 되어 있습니다. 무료 인스턴스는 유휴 시 정지될 수 있어 첫 요청의 응답이 느릴 수 있습니다.

환경 변수는 Render 대시보드에서 비밀값으로 설정합니다. `HEXORA_API_TOKEN`은 HEXORA의 `HEXORA_MCP_API_TOKEN`과 같아야 하며, `MCP_ACCESS_TOKEN`은 ChatGPT 연결에 사용하는 별도 토큰입니다.

## ChatGPT 연결

서버를 HTTPS로 배포한 뒤 ChatGPT의 사용자 설정에서 커스텀 MCP 서버 연결 기능을 사용할 수 있는 계정이라면 다음 값을 입력합니다.

- Server URL: `https://<Render 서비스 도메인>/mcp`
- Authentication: Bearer token
- Token: `MCP_ACCESS_TOKEN`

연결 후 도구 목록을 스캔하고, 읽기 도구를 먼저 확인합니다. `create_question`은 공개 DB에 실제 문항을 등록하므로 필요한 경우에만 활성화하고 명시적 요청이 있을 때만 사용합니다.

## 성취기준 데이터 범위

현재 HEXORA의 `CURRICULUM_STANDARDS` 데이터에는 `2015 개정 교육과정`의 일부 수학Ⅱ 성취기준이 포함되어 있습니다. API는 실제 등록된 데이터만 반환하며, 데이터가 없는 교육과정에 대해 성취기준을 만들어 내지 않습니다. `2022 개정 교육과정` 자료는 HEXORA의 원본 데이터가 추가된 뒤 검색할 수 있습니다.

## 테스트

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```
