from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="", max_length=200)
    subject: Literal["수학", "과학", "국어", "영어", "사회", "기타"]
    grade: str = Field(min_length=1, max_length=50)
    course: str = Field(default="", max_length=100)
    curriculum: Literal["2015 개정 교육과정", "2022 개정 교육과정"] = "2022 개정 교육과정"
    unit: str = Field(default="", max_length=200)
    achievement_standard: str = Field(default="", max_length=4000)
    difficulty: Literal["하", "중", "상"] = "중"
    question_type: Literal["객관식", "복수 선택", "단답형", "서술형"] = "단답형"
    points: int = Field(default=4, ge=1, le=100)
    prompt: str = Field(min_length=1, max_length=50000)
    choices: list[str] = Field(default_factory=list, max_length=20)
    answer: str = Field(min_length=1, max_length=10000)
    explanation: str = Field(default="", max_length=20000)
    source_type: Literal["직접 제작", "교재 및 참고서", "학교 시험", "수능 및 모의평가", "공개 데이터셋", "기타"] = "직접 제작"
    source: str = Field(default="", max_length=300)
    exam: str = Field(default="", max_length=200)
    original_question_number: str = Field(default="", max_length=50)
    source_url: str = Field(default="", max_length=1000)
    license: Literal["ORIGINAL", "CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "PERMISSION"] = "ORIGINAL"

    @field_validator("choices")
    @classmethod
    def choice_lengths(cls, values):
        if any(len(v) > 2000 for v in values):
            raise ValueError("각 선택지는 2,000자 이내여야 합니다.")
        return values
