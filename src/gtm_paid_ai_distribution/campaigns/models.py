"""Domain models.

Hierarchy:
    Campaign  (product, goal, budget, geography, audience)
      └── Experiment  (A/B arm: one marketing channel + one message + one landing page)
            └── MetricsSnapshot[]  (imported performance for that arm)

Audience (FR2) is campaign-scoped. Messaging (FR3) and the landing page (FR4)
live on the Experiment, so comparing a campaign's experiments *is* the A/B test
(FR8) and the best experiment is the "winning combination" (FR6).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class CampaignGoal(str, Enum):
    awareness = "awareness"
    traffic = "traffic"
    leads = "leads"
    sales = "sales"


class Channel(str, Enum):
    """Marketing channel an experiment runs on."""

    google = "google"
    linkedin = "linkedin"
    meta = "meta"
    tiktok = "tiktok"
    microsoft = "microsoft"
    x = "x"
    reddit = "reddit"


class CampaignStatus(str, Enum):
    draft = "draft"
    live = "live"
    paused = "paused"


class ExperimentStatus(str, Enum):
    draft = "draft"
    running = "running"
    paused = "paused"
    winner = "winner"
    archived = "archived"


class Audience(BaseModel):
    """FR2 — editable audience recommendation (campaign-scoped)."""

    icp: str = ""
    company_size: str = ""
    industries: list[str] = Field(default_factory=list)
    job_titles: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class MarketingMessage(BaseModel):
    """FR3 — the single message an experiment tests (images/video are Future)."""

    headline: str = ""
    description: str = ""
    cta: str = ""


class LandingPage(BaseModel):
    """FR4 — generated landing page content for an experiment."""

    hero: str = ""
    benefits: list[str] = Field(default_factory=list)
    testimonials: list[str] = Field(default_factory=list)
    faq: list[dict[str, str]] = Field(default_factory=list)  # {question, answer}
    cta: str = ""


class MetricsSnapshot(BaseModel):
    """FR5 — raw counters imported for an experiment at a point in time."""

    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    captured_at: datetime | None = None


class Experiment(BaseModel):
    """An A/B arm within a campaign (FR8)."""

    id: str = Field(default_factory=lambda: _new_id("exp"))
    name: str = "Untitled experiment"
    channel: Channel = Channel.linkedin
    status: ExperimentStatus = ExperimentStatus.draft
    message: MarketingMessage = Field(default_factory=MarketingMessage)
    landing_page: LandingPage = Field(default_factory=LandingPage)
    metrics: list[MetricsSnapshot] = Field(default_factory=list)


class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("cmp"))
    product_description: str
    goal: CampaignGoal = CampaignGoal.leads
    monthly_budget: float = 0.0
    geography: str = ""
    status: CampaignStatus = CampaignStatus.draft

    audience: Audience | None = None
    experiments: list[Experiment] = Field(default_factory=list)
