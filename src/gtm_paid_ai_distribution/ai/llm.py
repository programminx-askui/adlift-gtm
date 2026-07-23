"""Anthropic (Claude) client wrapper for structured generation + chat.

Used only when ``settings.chat_brain == "claude"``. The client resolves
credentials from the environment (``ANTHROPIC_API_KEY`` or an ``ant auth login``
profile) — never hardcode a key. Callers fall back to the stub generators if
this module raises, so the app keeps working without a key.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from ..config import settings

T = TypeVar("T", bound=BaseModel)


@lru_cache(maxsize=1)
def get_client() -> anthropic.Anthropic:
    """Lazily construct a shared Anthropic client.

    Uses the key from settings (read from ANTHROPIC_API_KEY / .env) when present;
    otherwise defers to the SDK's own credential resolution (env / `ant` profile).
    """
    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return anthropic.Anthropic()


def generate_structured(system: str, user: str, schema: type[T]) -> T:
    """Ask Claude for output validated against a Pydantic ``schema``.

    Uses ``messages.parse`` so the model is constrained to the schema and the
    SDK returns a validated instance (``parsed_output``).
    """
    response = get_client().messages.parse(
        model=settings.anthropic_model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    return response.parsed_output


def chat_reply(system: str, history: list[dict[str, str]], user_input: str) -> str:
    """Plain conversational reply. Adaptive thinking on; returns text only."""
    messages = [*history, {"role": "user", "content": user_input}]
    response = get_client().messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=system,
        thinking={"type": "adaptive"},
        messages=messages,
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()
