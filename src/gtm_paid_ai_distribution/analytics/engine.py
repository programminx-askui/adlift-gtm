"""Analytics engine (PRD FR5).

Pure functions that turn raw metric counters into the derived rates the
dashboard and the rules engine consume. No I/O, so it is trivially testable.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..campaigns.models import MetricsSnapshot


class DerivedMetrics(BaseModel):
    impressions: int
    clicks: int
    conversions: int
    spend: float
    revenue: float

    ctr: float  # clicks / impressions
    cpc: float  # spend / clicks
    cpa: float  # spend / conversions  (a.k.a. cost per lead)
    conversion_rate: float  # conversions / clicks
    roas: float  # revenue / spend


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def aggregate(snapshots: list[MetricsSnapshot]) -> MetricsSnapshot:
    """Sum raw counters across snapshots into a single total."""
    total = MetricsSnapshot()
    for s in snapshots:
        total.impressions += s.impressions
        total.clicks += s.clicks
        total.conversions += s.conversions
        total.spend += s.spend
        total.revenue += s.revenue
    return total


def derive(snapshot: MetricsSnapshot) -> DerivedMetrics:
    """Compute derived rates for a single (possibly aggregated) snapshot."""
    return DerivedMetrics(
        impressions=snapshot.impressions,
        clicks=snapshot.clicks,
        conversions=snapshot.conversions,
        spend=round(snapshot.spend, 2),
        revenue=round(snapshot.revenue, 2),
        ctr=round(_safe_div(snapshot.clicks, snapshot.impressions), 4),
        cpc=round(_safe_div(snapshot.spend, snapshot.clicks), 2),
        cpa=round(_safe_div(snapshot.spend, snapshot.conversions), 2),
        conversion_rate=round(_safe_div(snapshot.conversions, snapshot.clicks), 4),
        roas=round(_safe_div(snapshot.revenue, snapshot.spend), 2),
    )


def derive_totals(snapshots: list[MetricsSnapshot]) -> DerivedMetrics:
    return derive(aggregate(snapshots))
