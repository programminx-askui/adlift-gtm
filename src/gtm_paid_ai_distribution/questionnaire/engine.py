"""Loads the questionnaire definition and drives it question-by-question."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ..config import settings
from .models import Question, Questionnaire, QuestionnaireState


@lru_cache(maxsize=1)
def load_questionnaire(path: str | None = None) -> Questionnaire:
    """Load and validate the questionnaire YAML.

    Drop your own questions into `questionnaire/questions.yaml` (or point
    `GTM_QUESTIONNAIRE_PATH` at another file) and they flow through unchanged.
    """
    p = Path(path) if path else settings.questionnaire_path
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Questionnaire.model_validate(data)


class QuestionnaireEngine:
    """Stateless-per-call driver operating on an explicit state object."""

    def __init__(self, questionnaire: Questionnaire | None = None) -> None:
        self.questionnaire = questionnaire or load_questionnaire()

    def start(self) -> QuestionnaireState:
        return QuestionnaireState(questionnaire_id=self.questionnaire.id)

    def current_question(self, state: QuestionnaireState) -> Question | None:
        if state.complete or state.current_index >= len(self.questionnaire.questions):
            return None
        return self.questionnaire.questions[state.current_index]

    def submit(self, state: QuestionnaireState, answer: object) -> QuestionnaireState:
        """Record an answer for the current question and advance."""
        question = self.current_question(state)
        if question is None:
            return state
        if question.required and (answer is None or answer == ""):
            raise ValueError(f"Question {question.id!r} is required.")

        state.answers[question.id] = answer
        state.current_index += 1
        if state.current_index >= len(self.questionnaire.questions):
            state.complete = True
        return state
