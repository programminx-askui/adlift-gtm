"""In-memory campaign repository.

Swap for a real database before persistence matters; the service layer only
depends on these method signatures.
"""

from __future__ import annotations

from .models import Campaign


class CampaignStore:
    def __init__(self) -> None:
        self._campaigns: dict[str, Campaign] = {}

    def save(self, campaign: Campaign) -> Campaign:
        self._campaigns[campaign.id] = campaign
        return campaign

    def get(self, campaign_id: str) -> Campaign | None:
        return self._campaigns.get(campaign_id)

    def list(self) -> list[Campaign]:
        return list(self._campaigns.values())


store = CampaignStore()
