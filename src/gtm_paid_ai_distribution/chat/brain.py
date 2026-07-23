"""The chatbot 'brain' — pluggable so the stub can be swapped for a real LLM.

Today only a stub implementation exists. When you're ready to use Claude,
add a `ClaudeBrain` here and select it via `settings.chat_brain`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Message:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatContext:
    """Everything the brain may use to craft a reply."""

    history: list[Message] = field(default_factory=list)
    # Answers collected so far by the questionnaire engine.
    answers: dict[str, object] = field(default_factory=dict)


class Brain(Protocol):
    """A chatbot brain turns the latest user turn + context into a reply."""

    def reply(self, user_input: str, context: ChatContext) -> str: ...


class StubBrain:
    """Deterministic placeholder responder — no external calls.

    It simply reflects the input and nudges the conversation forward so the
    end-to-end flow (API -> brain -> UI) can be exercised before an LLM exists.
    """

    def reply(self, user_input: str, context: ChatContext) -> str:
        turn = len([m for m in context.history if m.role == "user"])
        return (
            f"(stub brain) You said: {user_input!r}. "
            f"This is turn {turn}. Set GTM_CHAT_BRAIN=claude to use a real LLM."
        )


_SYSTEM = (
    "You are the assistant for an AI Campaign Optimizer for B2B SaaS. Help the "
    "user create and improve paid campaigns (audiences, messaging, landing "
    "pages, experiments). Be concise and concrete."
)


class ClaudeBrain:
    """Real LLM brain backed by Anthropic's Claude (see `ai.llm`).

    The Anthropic client is constructed lazily inside `ai.llm`, so importing or
    instantiating this class never requires an API key — only `reply()` does.
    """

    def reply(self, user_input: str, context: ChatContext) -> str:
        from ..ai import llm

        # The caller appends the current user turn to history before calling us;
        # drop it so chat_reply doesn't send the message twice.
        prior = context.history
        if prior and prior[-1].role == "user" and prior[-1].content == user_input:
            prior = prior[:-1]
        history = [{"role": m.role, "content": m.content} for m in prior]
        return llm.chat_reply(_SYSTEM, history, user_input)


def get_brain(name: str) -> Brain:
    """Factory: resolve a brain by name (from settings)."""
    if name == "stub":
        return StubBrain()
    if name == "claude":
        return ClaudeBrain()
    raise ValueError(f"Unknown chat brain: {name!r}")
