"""AI generation services (PRD FR2-FR4): audience, messages, landing page.

Two backends behind one interface:
  - "stub" (default): deterministic, no external calls — runs with no API key.
  - "claude": real generation via `ai.llm` when `settings.chat_brain == "claude"`.

The public functions dispatch on `settings.use_llm` and fall back to the stub on
any LLM error, so a missing key or transient failure never breaks the flow.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from ..campaigns.models import (
    Audience,
    CampaignGoal,
    Channel,
    Experiment,
    ExperimentStatus,
    LandingPage,
    MarketingMessage,
)
from ..config import settings

logger = logging.getLogger(__name__)


def _core(product: str) -> str:
    return product.strip().rstrip(".") or "Your Product"


# --- Schema-friendly LLM response models (mapped to domain models) ---------
class _FaqItem(BaseModel):
    question: str
    answer: str


class _LandingPageOut(BaseModel):
    hero: str
    benefits: list[str]
    testimonials: list[str]
    faq: list[_FaqItem]
    cta: str


class _MessagesOut(BaseModel):
    variants: list[MarketingMessage] = Field(default_factory=list)


_SYSTEM = (
    "You are a B2B SaaS paid-acquisition expert. Be concrete, specific, and "
    "concise. Return only what the schema asks for."
)


# --- Audience (FR2) --------------------------------------------------------
def _stub_audience(product_description: str, goal: CampaignGoal) -> Audience:
    return Audience(
        icp="B2B SaaS decision-makers relevant to the described product",
        company_size="50-500 employees",
        industries=["SaaS", "FinTech", "Cybersecurity"],
        job_titles=["VP Sales", "RevOps", "Sales Manager"],
        keywords=[w for w in _core(product_description).lower().split() if len(w) > 3][:6],
        exclusions=["students", "job seekers"],
    )


def generate_audience(product_description: str, goal: CampaignGoal) -> Audience:
    if settings.use_llm:
        try:
            from . import llm

            return llm.generate_structured(
                _SYSTEM,
                f"Product: {product_description}\nCampaign goal: {goal.value}\n"
                "Recommend the ideal customer profile (ICP), company size, "
                "industries, job titles, target keywords, and audience exclusions.",
                Audience,
            )
        except Exception:  # noqa: BLE001 — fall back to stub on any LLM failure
            logger.warning("LLM audience generation failed; using stub", exc_info=True)
    return _stub_audience(product_description, goal)


# --- Messages (FR3) --------------------------------------------------------
_HEADLINE_ANGLES = [
    ("Stop Wasting Time — {core}", "Book a demo"),
    ("{core}", "Start free trial"),
    ("Double Your Results with {core}", "Learn more"),
]


def _stub_messages(
    product_description: str, goal: CampaignGoal, count: int
) -> list[MarketingMessage]:
    core = _core(product_description)
    count = max(1, min(count, len(_HEADLINE_ANGLES)))
    return [
        MarketingMessage(
            headline=tmpl.format(core=core),
            description=f"{core}. Built for B2B SaaS teams that want measurable growth.",
            cta=cta,
        )
        for tmpl, cta in _HEADLINE_ANGLES[:count]
    ]


def generate_messages(
    product_description: str, goal: CampaignGoal, count: int = 2
) -> list[MarketingMessage]:
    """FR3 — generate `count` distinct message variants for A/B testing."""
    count = max(1, count)
    if settings.use_llm:
        try:
            from . import llm

            out = llm.generate_structured(
                _SYSTEM,
                f"Product: {product_description}\nCampaign goal: {goal.value}\n"
                f"Write {count} distinct ad message variants for A/B testing. "
                "Each has a punchy headline, a one-sentence description, and a CTA.",
                _MessagesOut,
            )
            variants = out.variants[:count]
            if variants:
                return variants
        except Exception:  # noqa: BLE001
            logger.warning("LLM message generation failed; using stub", exc_info=True)
    return _stub_messages(product_description, goal, count)


# --- Landing page (FR4) ----------------------------------------------------
def _stub_landing_page(product_description: str, goal: CampaignGoal) -> LandingPage:
    core = _core(product_description)
    return LandingPage(
        hero=core,
        benefits=["Set up in minutes", "Measurable ROI", "Built for B2B SaaS growth teams"],
        testimonials=["'Cut our cost per lead by 25%.' — Head of Growth"],
        faq=[
            {"question": "How does it work?", "answer": f"{core} — automatically."},
            {"question": "How long to set up?", "answer": "Under 20 minutes."},
        ],
        cta="Book a demo",
    )


def generate_landing_page(product_description: str, goal: CampaignGoal) -> LandingPage:
    if settings.use_llm:
        try:
            from . import llm

            out = llm.generate_structured(
                _SYSTEM,
                f"Product: {product_description}\nCampaign goal: {goal.value}\n"
                "Write landing page content: a hero line, 3 benefits, 1-2 short "
                "testimonials, 2 FAQ entries, and a CTA.",
                _LandingPageOut,
            )
            return LandingPage(
                hero=out.hero,
                benefits=out.benefits,
                testimonials=out.testimonials,
                faq=[{"question": f.question, "answer": f.answer} for f in out.faq],
                cta=out.cta,
            )
        except Exception:  # noqa: BLE001
            logger.warning("LLM landing-page generation failed; using stub", exc_info=True)
    return _stub_landing_page(product_description, goal)


# --- A/B seeding -----------------------------------------------------------
def seed_experiments(
    product_description: str,
    goal: CampaignGoal,
    channel: Channel = Channel.linkedin,
    count: int = 2,
) -> list[Experiment]:
    """Create the initial A/B arms: one experiment per message variant."""
    landing = generate_landing_page(product_description, goal)
    messages = generate_messages(product_description, goal, count)
    return [
        Experiment(
            name=f"Variant {chr(ord('A') + i)}",
            channel=channel,
            status=ExperimentStatus.draft,
            message=msg,
            landing_page=landing.model_copy(deep=True),
        )
        for i, msg in enumerate(messages)
    ]
