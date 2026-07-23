"""Data models for the data-driven questionnaire."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    text = "text"
    number = "number"
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    boolean = "boolean"


class Question(BaseModel):
    id: str
    prompt: str
    type: QuestionType = QuestionType.text
    required: bool = True
    # For choice questions.
    options: list[str] = Field(default_factory=list)
    help_text: str | None = None


class Questionnaire(BaseModel):
    id: str
    title: str
    description: str | None = None
    questions: list[Question]


class QuestionnaireState(BaseModel):
    """Tracks progress through a questionnaire for one session."""

    questionnaire_id: str
    current_index: int = 0
    answers: dict[str, object] = Field(default_factory=dict)
    complete: bool = False
