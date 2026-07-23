"""Insights + optimization (PRD FR6, FR7).

A deterministic RULES ENGINE over the analytics output — the "Rules Engine" AI
component in the PRD; no LLM required. Insights compare a campaign's
experiments (A/B arms) to surface the winning combination, weak creatives, and
budget inefficiencies. A future version can ask the LLM to phrase richer
recommendations.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from ..analytics.engine import DerivedMetrics, derive_totals
from ..campaigns.models import Campaign, Experiment

# Heuristic thresholds — tune freely.
LOW_CTR = 0.02
LOW_CONVERSION_RATE = 0.02
MIN_ROAS = 1.0
EXPERIMENT_MIN_CONVERSIONS = 5


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    action = "action"


class Insight(BaseModel):
    title: str
    detail: str
    severity: Severity = Severity.info


class OptimizationSuggestion(BaseModel):
    action: str  # e.g. "pause_experiment", "scale_experiment", "replace_message"
    target: str  # experiment id or name
    rationale: str


class ExperimentAnalysis(BaseModel):
    experiment_id: str
    name: str
    channel: str
    metrics: DerivedMetrics


class CampaignAnalysis(BaseModel):
    totals: DerivedMetrics
    experiments: list[ExperimentAnalysis]
    insights: list[Insight]
    suggestions: list[OptimizationSuggestion]


def analyze_experiment(experiment: Experiment) -> DerivedMetrics:
    """FR5 — derived metrics for a single experiment."""
    return derive_totals(experiment.metrics)


def analyze_campaign(campaign: Campaign) -> CampaignAnalysis:
    """FR5/FR6/FR7 — aggregate, compare experiments, and recommend actions."""
    per_experiment = [
        ExperimentAnalysis(
            experiment_id=e.id,
            name=e.name,
            channel=e.channel.value,
            metrics=analyze_experiment(e),
        )
        for e in campaign.experiments
    ]
    totals = derive_totals(
        [snap for e in campaign.experiments for snap in e.metrics]
    )

    insights: list[Insight] = []
    suggestions: list[OptimizationSuggestion] = []

    # --- Per-experiment creative / landing signals -----------------------
    for ea in per_experiment:
        m = ea.metrics
        if m.impressions and m.ctr < LOW_CTR:
            insights.append(
                Insight(
                    title=f"Low CTR on {ea.name}",
                    detail=f"CTR is {m.ctr:.1%} (below {LOW_CTR:.0%}).",
                    severity=Severity.warning,
                )
            )
            suggestions.append(
                OptimizationSuggestion(
                    action="replace_message",
                    target=ea.name,
                    rationale="Low CTR usually means the headline is not resonating.",
                )
            )
            suggestions.append(
                OptimizationSuggestion(
                    action="new_cta",
                    target=ea.name,
                    rationale="Try a stronger call-to-action to lift click-through.",
                )
            )
        if m.clicks and m.conversion_rate < LOW_CONVERSION_RATE:
            insights.append(
                Insight(
                    title=f"Low conversion on {ea.name}",
                    detail=f"Conversion rate is {m.conversion_rate:.1%}; clicks aren't converting.",
                    severity=Severity.warning,
                )
            )
            suggestions.append(
                OptimizationSuggestion(
                    action="revise_landing_page",
                    target=ea.name,
                    rationale="Good clicks with poor conversion points at the landing page.",
                )
            )

    # --- Overall profitability -------------------------------------------
    if totals.spend and totals.roas < MIN_ROAS:
        insights.append(
            Insight(
                title="Campaign not yet profitable",
                detail=f"ROAS is {totals.roas:.2f}x (below {MIN_ROAS:.0f}x).",
                severity=Severity.action,
            )
        )

    # Poor conversion across the whole campaign points at audience/targeting.
    if totals.clicks and totals.conversion_rate < LOW_CONVERSION_RATE:
        suggestions.append(
            OptimizationSuggestion(
                action="new_audience",
                target=campaign.id,
                rationale=(
                    "Clicks aren't converting campaign-wide — test a tighter or "
                    "different audience (ICP, industries, or job titles)."
                ),
            )
        )

    # --- A/B comparison: winning combination -----------------------------
    ranked = [
        ea
        for ea in per_experiment
        if ea.metrics.conversions >= EXPERIMENT_MIN_CONVERSIONS
    ]
    if len(ranked) >= 2:
        ranked.sort(key=lambda ea: ea.metrics.cpa)  # lower CPA wins
        best, worst = ranked[0], ranked[-1]
        insights.append(
            Insight(
                title="Winning combination",
                detail=(
                    f"{best.name} ({best.channel}) leads at CPA ${best.metrics.cpa:.0f}; "
                    f"{worst.name} lags at ${worst.metrics.cpa:.0f}."
                ),
                severity=Severity.info,
            )
        )
        suggestions.append(
            OptimizationSuggestion(
                action="scale_experiment",
                target=best.name,
                rationale=f"Lowest CPA (${best.metrics.cpa:.0f}) — shift budget here.",
            )
        )
        suggestions.append(
            OptimizationSuggestion(
                action="pause_experiment",
                target=worst.name,
                rationale=f"Highest CPA (${worst.metrics.cpa:.0f}).",
            )
        )

    if not insights:
        insights.append(
            Insight(
                title="Not enough data yet",
                detail="Import performance data on the experiments to unlock recommendations.",
            )
        )

    return CampaignAnalysis(
        totals=totals,
        experiments=per_experiment,
        insights=insights,
        suggestions=suggestions,
    )
