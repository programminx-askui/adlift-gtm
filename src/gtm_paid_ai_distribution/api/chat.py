"""Chat endpoints: talk to the (currently stubbed) chatbot brain."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..chat.brain import ChatContext, Message, get_brain
from ..config import settings
from ..sessions import store

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    session = store.get_or_create(req.session_id)
    brain = get_brain(settings.chat_brain)

    session.history.append(Message(role="user", content=req.message))
    context = ChatContext(
        history=session.history,
        answers=session.questionnaire.answers if session.questionnaire else {},
    )
    reply = brain.reply(req.message, context)
    session.history.append(Message(role="assistant", content=reply))

    return ChatResponse(session_id=session.id, reply=reply)
