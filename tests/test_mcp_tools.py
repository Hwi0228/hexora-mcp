import asyncio
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

import server
from hexora_mcp.schemas import QuestionInput


def sample_question(**overrides):
    question = {
        "subject": "수학",
        "grade": "고2",
        "course": "수학Ⅱ",
        "curriculum": "2015 개정 교육과정",
        "prompt": "함수 f(x)=x^2의 도함수를 구하여라.",
        "answer": "2x",
        "choices": ["첫 번째", "두 번째"],
    }
    question.update(overrides)
    return question


def test_question_schema_accepts_supported_payload():
    parsed = QuestionInput.model_validate(sample_question())

    assert parsed.subject == "수학"
    assert parsed.grade == "고2"
    assert parsed.choices == ["첫 번째", "두 번째"]


def test_question_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        QuestionInput.model_validate(sample_question(unexpected="value"))


def test_question_schema_rejects_invalid_subject():
    with pytest.raises(ValidationError):
        QuestionInput.model_validate(sample_question(subject="물리"))


def test_health_check_uses_hexora_api(monkeypatch):
    request = AsyncMock(return_value={"ok": True, "service": "HEXORA"})
    monkeypatch.setattr(server.api, "request", request)

    result = asyncio.run(server.health_check())

    assert result["ok"] is True
    request.assert_awaited_once_with("GET", "/health")


def test_search_questions_validates_limit_and_forwards_filters(monkeypatch):
    request = AsyncMock(return_value={"ok": True, "count": 1})
    monkeypatch.setattr(server.api, "request", request)

    invalid = asyncio.run(server.search_questions(limit=0))
    assert invalid["ok"] is False
    request.assert_not_awaited()

    result = asyncio.run(
        server.search_questions(query="도함수", course="수학Ⅱ", limit=5)
    )

    assert result["count"] == 1
    args = request.await_args
    assert args.args == ("GET", "/questions")
    assert args.kwargs["params"]["query"] == "도함수"
    assert args.kwargs["params"]["course"] == "수학Ⅱ"
    assert args.kwargs["params"]["limit"] == 5


def test_get_question_requires_six_character_base36_code(monkeypatch):
    request = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(server.api, "request", request)

    invalid = asyncio.run(server.get_question("123"))
    assert invalid["ok"] is False
    request.assert_not_awaited()

    asyncio.run(server.get_question(" ab12cd "))
    request.assert_awaited_once_with("GET", "/questions/AB12CD")


def test_get_standards_validates_limit(monkeypatch):
    request = AsyncMock(return_value={"ok": True})
    monkeypatch.setattr(server.api, "request", request)

    invalid = asyncio.run(server.get_standards(limit=101))
    assert invalid["ok"] is False
    request.assert_not_awaited()

    asyncio.run(server.get_standards(query="미분", course="수학Ⅱ", limit=20))
    args = request.await_args
    assert args.args == ("GET", "/standards")
    assert args.kwargs["params"]["query"] == "미분"
    assert args.kwargs["params"]["course"] == "수학Ⅱ"
    assert args.kwargs["params"]["limit"] == 20


def test_validate_question_never_saves(monkeypatch):
    request = AsyncMock(return_value={"ok": True, "valid": True})
    monkeypatch.setattr(server.api, "request", request)

    result = asyncio.run(server.validate_question(sample_question()))

    assert result["valid"] is True
    request.assert_awaited_once()
    assert request.await_args.args == ("POST", "/questions/validate")


def test_create_question_validates_before_persisting(monkeypatch):
    request = AsyncMock(
        side_effect=[
            {"ok": True, "valid": True},
            {"ok": True, "created": True, "code": "000001"},
        ]
    )
    monkeypatch.setattr(server.api, "request", request)

    result = asyncio.run(server.create_question(sample_question()))

    assert result["created"] is True
    assert result["code"] == "000001"
    assert request.await_count == 2
    assert request.await_args_list[0].args == ("POST", "/questions/validate")
    assert request.await_args_list[1].args == ("POST", "/questions")


def test_create_question_stops_when_validation_fails(monkeypatch):
    request = AsyncMock(return_value={"ok": True, "valid": False, "errors": ["오류"]})
    monkeypatch.setattr(server.api, "request", request)

    result = asyncio.run(server.create_question(sample_question()))

    assert result["created"] is False
    assert result["validation"]["valid"] is False
    request.assert_awaited_once()
