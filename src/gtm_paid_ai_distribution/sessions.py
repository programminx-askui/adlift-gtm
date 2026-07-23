"""In-memory session store.

Good enough for local dev and the stubbed flow. Replace with Redis/DB before
running multiple workers or persisting across restarts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from .chat.brain import Message
from .questionnaire.models import QuestionnaireState


@dataclass
class Session:
    id: str
    history: list[Message] = field(default_factory=list)
    questionnaire: QuestionnaireState | None = None


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        session = Session(id=uuid4().hex)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> Session:
        if session_id:
            existing = self.get(session_id)
            if existing:
                return existing
        return self.create()


store = SessionStore()
