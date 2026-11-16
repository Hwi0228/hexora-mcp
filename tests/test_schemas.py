import pytest
from pydantic import ValidationError

from hexora_mcp.schemas import QuestionInput


def sample():
    return {"subject": "수학", "grade": "고등학교 2학년",
            "prompt": "함수 $f(x)=x^2$의 도함수를 구하여라.", "answer": "$2x$"}


def test_defaults():
    q = QuestionInput.model_validate(sample())
    assert q.difficulty == "중" and q.points == 4 and q.choices == []


def test_prompt_required():
    d = sample()
    d.pop("prompt")
    with pytest.raises(ValidationError):
        QuestionInput.model_validate(d)


def test_extra_fields_forbidden():
    d = sample()
    d["sql"] = "DROP TABLE questions"
    with pytest.raises(ValidationError):
        QuestionInput.model_validate(d)


def test_choice_length_limit():
    d = sample()
    d["choices"] = ["x" * 2001]
    with pytest.raises(ValidationError):
        QuestionInput.model_validate(d)
