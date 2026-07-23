"""Example campaigns seeded on startup so the app isn't empty on first open.

Built directly from domain models (no AI/LLM calls) so seeding is deterministic
and offline. Runs only when the store is empty and `settings.seed_examples` is on.
"""

from __future__ import annotations

from .models import (
    Audience,
    Campaign,
    CampaignGoal,
    CampaignStatus,
    Channel,
    Experiment,
    ExperimentStatus,
    LandingPage,
    MarketingMessage,
    MetricsSnapshot,
)
from .store import CampaignStore, store


def _landing(hero: str, benefits: list[str]) -> LandingPage:
    return LandingPage(
        hero=hero,
        benefits=benefits,
        testimonials=["'Cut our cost per lead by 25% in the first month.' — Head of Growth"],
        faq=[
            {"question": "How does it work?", "answer": f"{hero} — automatically."},
            {"question": "How long to set up?", "answer": "Under 20 minutes."},
        ],
        cta="Book a demo",
    )


def _sdr_campaign() -> Campaign:
    """The PRD example: an AI SDR platform, with a clear A/B winner."""
    winner = Experiment(
        name="Variant A",
        channel=Channel.linkedin,
        status=ExperimentStatus.winner,
        message=MarketingMessage(
            headline="Stop Wasting SDR Time",
            description="AI researches every account before your SDR reaches out.",
            cta="Book a demo",
        ),
        landing_page=_landing(
            "Automate SDR Research",
            ["Research every account automatically", "2× SDR productivity", "Book more qualified demos"],
        ),
        metrics=[
            MetricsSnapshot(impressions=12000, clicks=372, conversions=22, spend=1900, revenue=4400)
        ],
    )
    laggard = Experiment(
        name="Variant B",
        channel=Channel.google,
        status=ExperimentStatus.running,
        message=MarketingMessage(
            headline="Automate Account Research",
            description="Give your SDRs an AI research assistant for every account.",
            cta="Start free trial",
        ),
        landing_page=_landing(
            "AI Account Research for SDRs",
            ["Instant account briefs", "CRM-ready notes", "Less manual prep"],
        ),
        metrics=[
            MetricsSnapshot(impressions=9000, clicks=210, conversions=6, spend=1500, revenue=900)
        ],
    )
    return Campaign(
        product_description="We help SDR teams automate account research.",
        goal=CampaignGoal.leads,
        monthly_budget=6000,
        geography="United States",
        status=CampaignStatus.live,
        audience=Audience(
            icp="Revenue teams doing outbound sales",
            company_size="50-500 employees",
            industries=["SaaS", "FinTech", "Cybersecurity"],
            job_titles=["VP Sales", "RevOps", "Sales Manager"],
            keywords=["sdr", "account research", "outbound", "sales automation"],
            exclusions=["students", "job seekers"],
        ),
        experiments=[winner, laggard],
    )


def _expense_campaign() -> Campaign:
    """A second example with only partial data (shows the 'needs data' state)."""
    return Campaign(
        product_description="AI-powered expense management for finance teams.",
        goal=CampaignGoal.sales,
        monthly_budget=9000,
        geography="DACH",
        status=CampaignStatus.draft,
        audience=Audience(
            icp="Finance and operations leaders at mid-market companies",
            company_size="200-1000 employees",
            industries=["SaaS", "Manufacturing", "Retail"],
            job_titles=["CFO", "Finance Manager", "Controller"],
            keywords=["expense management", "spend control", "finance automation"],
            exclusions=["personal finance", "students"],
        ),
        experiments=[
            Experiment(
                name="Variant A",
                channel=Channel.linkedin,
                status=ExperimentStatus.draft,
                message=MarketingMessage(
                    headline="Close the Books 5 Days Faster",
                    description="AI categorizes every expense and flags anomalies automatically.",
                    cta="Book a demo",
                ),
                landing_page=_landing(
                    "Faster Close, Fewer Errors",
                    ["Auto-categorized expenses", "Real-time policy checks", "Audit-ready reports"],
                ),
            ),
            Experiment(
                name="Variant B",
                channel=Channel.meta,
                status=ExperimentStatus.draft,
                message=MarketingMessage(
                    headline="Expense Management on Autopilot",
                    description="Let AI handle categorization, approvals, and anomaly detection.",
                    cta="Start free trial",
                ),
                landing_page=_landing(
                    "Expense Management on Autopilot",
                    ["Zero manual entry", "Instant approvals", "Anomaly alerts"],
                ),
            ),
        ],
    )


def seed_examples(repo: CampaignStore | None = None) -> int:
    """Seed example campaigns if the store is empty. Returns count added."""
    repo = repo or store
    if repo.list():
        return 0
    for factory in (_sdr_campaign, _expense_campaign):
        repo.save(factory())
    return len(repo.list())
