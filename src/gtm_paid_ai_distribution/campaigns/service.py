"""Orchestrates campaigns and their experiments.

The API layer calls this: create a campaign (audience + seeded A/B experiments),
manage experiments, import per-experiment metrics, and edit generated assets.
"""

from __future__ import annotations

from ..ai.generation import (
    generate_audience,
    generate_landing_page,
    generate_messages,
    seed_experiments,
)
from .models import (
    Campaign,
    CampaignGoal,
    Channel,
    Experiment,
    MetricsSnapshot,
)
from .store import CampaignStore, store


class CampaignService:
    def __init__(self, repo: CampaignStore | None = None) -> None:
        self.repo = repo or store

    # --- Campaigns -------------------------------------------------------
    def create(
        self,
        product_description: str,
        goal: CampaignGoal = CampaignGoal.leads,
        monthly_budget: float = 0.0,
        geography: str = "",
        generate: bool = True,
    ) -> Campaign:
        """Create a draft (FR1); optionally generate audience + A/B arms (FR2-FR4)."""
        campaign = Campaign(
            product_description=product_description,
            goal=goal,
            monthly_budget=monthly_budget,
            geography=geography,
        )
        if generate:
            campaign.audience = generate_audience(product_description, goal)
            campaign.experiments = seed_experiments(product_description, goal)
        return self.repo.save(campaign)

    def get(self, campaign_id: str) -> Campaign | None:
        return self.repo.get(campaign_id)

    def update(self, campaign_id: str, changes: dict[str, object]) -> Campaign | None:
        campaign = self.repo.get(campaign_id)
        if campaign is None:
            return None
        updated = campaign.model_copy(update=changes)
        return self.repo.save(updated)

    # --- Experiments -----------------------------------------------------
    def find_experiment(self, experiment_id: str) -> tuple[Campaign, Experiment] | None:
        for campaign in self.repo.list():
            for exp in campaign.experiments:
                if exp.id == experiment_id:
                    return campaign, exp
        return None

    def add_experiment(
        self, campaign_id: str, experiment: Experiment
    ) -> Experiment | None:
        campaign = self.repo.get(campaign_id)
        if campaign is None:
            return None
        campaign.experiments.append(experiment)
        self.repo.save(campaign)
        return experiment

    def generate_experiment(
        self, campaign_id: str, channel: Channel = Channel.linkedin
    ) -> Experiment | None:
        """Create one new AI-generated experiment arm for a campaign."""
        campaign = self.repo.get(campaign_id)
        if campaign is None:
            return None
        messages = generate_messages(campaign.product_description, campaign.goal, count=1)
        landing = generate_landing_page(campaign.product_description, campaign.goal)
        exp = Experiment(
            name=f"Variant {chr(ord('A') + len(campaign.experiments))}",
            channel=channel,
            message=messages[0],
            landing_page=landing,
        )
        campaign.experiments.append(exp)
        self.repo.save(campaign)
        return exp

    def update_experiment(
        self, experiment_id: str, changes: dict[str, object]
    ) -> Experiment | None:
        found = self.find_experiment(experiment_id)
        if found is None:
            return None
        campaign, exp = found
        updated = exp.model_copy(update=changes)
        exp_index = campaign.experiments.index(exp)
        campaign.experiments[exp_index] = updated
        self.repo.save(campaign)
        return updated

    def import_metrics(
        self, experiment_id: str, snapshots: list[MetricsSnapshot]
    ) -> Experiment | None:
        """FR5 — attach imported performance data to one experiment."""
        found = self.find_experiment(experiment_id)
        if found is None:
            return None
        campaign, exp = found
        exp.metrics.extend(snapshots)
        self.repo.save(campaign)
        return exp


service = CampaignService()
