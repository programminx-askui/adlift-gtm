"""Test isolation.

Force the deterministic stub brain for the whole suite so tests never depend on
a developer's local `.env` (which may set GTM_CHAT_BRAIN=claude) or make real
Anthropic API calls. Tests that specifically need LLM behavior should mock it.
"""

from __future__ import annotations

import pytest

from gtm_paid_ai_distribution.config import settings


@pytest.fixture(autouse=True)
def _force_stub_brain():
    previous = settings.chat_brain
    settings.chat_brain = "stub"
    yield
    settings.chat_brain = previous
