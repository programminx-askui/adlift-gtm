"""Questionnaire (Campaign Creation wizard, FR1) endpoints.

Drives the data-driven wizard one question at a time and, on completion,
hands the answers to the campaign service to create a draft.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..campaigns.models import Campaign, CampaignGoal
from ..campaigns.service import service as campaign_service
from ..questionnaire.engine import QuestionnaireEngine
from ..questionnaire.models import Question, QuestionnaireState
from ..sessions import store as session_store

router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])
engine = QuestionnaireEngine()


class StartResponse(BaseModel):
    session_id: str
    question: Question | None


class AnswerRequest(BaseModel):
    session_id: str
    answer: object


class AnswerResponse(BaseModel):
    session_id: str
    question: Question | None
    complete: bool
    answers: dict[str, object]
    campaign: Campaign | None = None


def _state(session_id: str | None) -> tuple[str, QuestionnaireState]:
    session = session_store.get_or_create(session_id)
    if session.questionnaire is None:
        session.questionnaire = engine.start()
    return session.id, session.questionnaire


@router.post("/start", response_model=StartResponse)
def start() -> StartResponse:
    session = session_store.create()
    session.questionnaire = engine.start()
    return StartResponse(
        session_id=session.id,
        question=engine.current_question(session.questionnaire),
    )


@router.post("/answer", response_model=AnswerResponse)
def answer(req: AnswerRequest) -> AnswerResponse:
    session = session_store.get(req.session_id)
    if session is None or session.questionnaire is None:
        raise HTTPException(status_code=404, detail="No active questionnaire session")

    try:
        state = engine.submit(session.questionnaire, req.answer)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    campaign: Campaign | None = None
    if state.complete:
        campaign = _campaign_from_answers(state.answers)

    return AnswerResponse(
        session_id=session.id,
        question=engine.current_question(state),
        complete=state.complete,
        answers=state.answers,
        campaign=campaign,
    )


def _campaign_from_answers(answers: dict[str, object]) -> Campaign:
    """Map completed wizard answers onto a generated campaign draft."""
    goal_raw = str(answers.get("goal", "leads"))
    try:
        goal = CampaignGoal(goal_raw)
    except ValueError:
        goal = CampaignGoal.leads
    try:
        budget = float(answers.get("monthly_budget") or 0)
    except (TypeError, ValueError):
        budget = 0.0

    return campaign_service.create(
        product_description=str(answers.get("product_description", "")),
        goal=goal,
        monthly_budget=budget,
        geography=str(answers.get("geography", "")),
        generate=True,
    )
