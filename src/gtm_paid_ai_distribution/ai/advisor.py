"""Claude-backed campaign advisor.

Turns a campaign (audience + experiments + computed metrics) into prioritized,
written improvement recommendations. This is the LLM counterpart to the
deterministic rules engine in `ai.insights` — it requires `settings.use_llm`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..campaigns.models import Campaign
from .insights import analyze_campaign


class AiRecommendation(BaseModel):
    title: str
    rationale: str
    suggested_action: str
    priority: str = "medium"  # high | medium | low


class AiRecommendations(BaseModel):
    summary: str
    recommendations: list[AiRecommendation] = Field(default_factory=list)


_SYSTEM = (
    "You are a senior B2B SaaS paid-acquisition strategist. Given a campaign and "
    "its performance data, return specific, prioritized improvements — not generic "
    "advice. Reference the actual numbers and experiments. Cover audience, "
    "messaging, landing pages, budget allocation across experiments, and which "
    "experiment to run next. Keep each recommendation concrete and actionable."
)


def _context(campaign: Campaign) -> str:
    an = analyze_campaign(campaign)
    t = an.totals
    lines = [
        f"Product: {campaign.product_description}",
        f"Goal: {campaign.goal.value}; monthly budget: ${campaign.monthly_budget}; "
        f"geography: {campaign.geography or 'unspecified'}",
    ]
    if campaign.audience:
        a = campaign.audience
        lines.append(
            f"Audience: {a.icp}; {a.company_size}; industries: "
            f"{', '.join(a.industries)}; titles: {', '.join(a.job_titles)}"
        )
    lines.append(
        f"Totals: impressions {t.impressions}, CTR {t.ctr:.2%}, CPA ${t.cpa}, "
        f"conversion rate {t.conversion_rate:.2%}, ROAS {t.roas}x, spend ${t.spend}"
    )
    by_id = {e.experiment_id: e.metrics for e in an.experiments}
    lines.append("Experiments (A/B arms):")
    for exp in campaign.experiments:
        m = by_id.get(exp.id)
        perf = (
            f"impressions {m.impressions}, CTR {m.ctr:.2%}, CPA ${m.cpa}, "
            f"conversions {m.conversions}, ROAS {m.roas}x"
            if m and m.impressions
            else "no performance data yet"
        )
        lines.append(
            f"- {exp.name} [{exp.channel.value}] status={exp.status.value} "
            f"headline={exp.message.headline!r} cta={exp.message.cta!r} — {perf}"
        )
    return "\n".join(lines)


def ai_recommendations(campaign: Campaign) -> AiRecommendations:
    """Ask Claude for prioritized improvements. Requires an LLM to be configured."""
    from . import llm

    return llm.generate_structured(_SYSTEM, _context(campaign), AiRecommendations)
