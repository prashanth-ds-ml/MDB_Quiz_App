from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

PoolType = Literal["learning", "exam"]
Confidence = Literal["high", "medium"]
Difficulty = Literal["easy", "medium", "hard"]
QType = Literal["single", "multi"]
Status = Literal["draft", "reviewed", "published", "archived"]

class ExamRelevance(BaseModel):
    pool: PoolType
    confidence: Confidence

class Choice(BaseModel):
    key: Literal["A", "B", "C", "D"]
    text: str

class Answer(BaseModel):
    keys: List[Literal["A", "B", "C", "D"]]

class Artifacts(BaseModel):
    sample_docs: List[dict] = Field(default_factory=list)
    snippets: List[dict] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

class Rationale(BaseModel):
    rule: str
    correct_why: List[str]
    wrong_why: Dict[str, str]
    trap: Optional[str] = None
    mini_demo: Optional[str] = None

    @field_validator("correct_why")
    @classmethod
    def correct_why_nonempty(cls, v):
        if not v or not any(s.strip() for s in v):
            raise ValueError("rationale.correct_why must contain at least 1 bullet")
        return v

class QuestionV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "2.0"
    id: str
    title: str
    topic: str
    subtopic: str
    difficulty: Difficulty
    type: QType
    tags: List[str] = Field(default_factory=list)

    exam_relevance: ExamRelevance

    prompt: str
    context: Optional[str] = None
    artifacts: Artifacts = Field(default_factory=Artifacts)

    choices: List[Choice]
    answer: Answer
    rationale: Rationale

    status: Status = "draft"
    author: str = "unknown"
    updated_at: str

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, choices: List[Choice]):
        keys = [c.key for c in choices]
        if sorted(keys) != ["A", "B", "C", "D"]:
            raise ValueError("choices must include exactly A, B, C, D")
        return choices

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, ans: Answer, info):
        # access other fields via info.data
        qtype = info.data.get("type")
        if qtype == "single" and len(ans.keys) != 1:
            raise ValueError("single choice questions must have exactly 1 correct answer")
        if qtype == "multi" and len(ans.keys) < 2:
            raise ValueError("multi-select questions must have at least 2 correct answers")
        return ans

    @field_validator("rationale")
    @classmethod
    def validate_wrong_why(cls, r: Rationale, info):
        # wrong_why should cover all incorrect options
        choices = info.data.get("choices", [])
        if not choices:
            return r
        correct = set(info.data.get("answer").keys) if info.data.get("answer") else set()
        all_keys = {c.key for c in choices}
        wrong_keys = sorted(list(all_keys - correct))
        missing = [k for k in wrong_keys if k not in r.wrong_why]
        if missing:
            raise ValueError(f"rationale.wrong_why missing explanations for: {missing}")
        return r
