"""A generic stub adapter used for every platform until real APIs are wired.

Each platform below is just a thin subclass setting `key`/`display_name`, so
replacing one with a real implementation is a localized change.
"""

from __future__ import annotations

from .base import (
    AdPlatformAdapter,
    Campaign,
    CampaignResult,
    ConnectionStatus,
)


class StubAdapter(AdPlatformAdapter):
    key = "stub"
    display_name = "Stub Platform"

    def __init__(self) -> None:
        self._connected = False

    def status(self) -> ConnectionStatus:
        return (
            ConnectionStatus.connected
            if self._connected
            else ConnectionStatus.disconnected
        )

    def connect(self, credentials: dict[str, object]) -> ConnectionStatus:
        # A real adapter would exchange credentials for a token here.
        self._connected = bool(credentials)
        return self.status()

    def create_campaign(self, campaign: Campaign) -> CampaignResult:
        return CampaignResult(
            platform=self.key,
            external_id=f"{self.key}-stub-0001",
            status="created (stub)",
            detail=f"Would create {campaign.name!r} on {self.display_name}.",
        )


class GoogleAdsAdapter(StubAdapter):
    key = "google"
    display_name = "Google Ads"


class MetaAdsAdapter(StubAdapter):
    key = "meta"
    display_name = "Meta Ads (Facebook / Instagram)"


class LinkedInAdsAdapter(StubAdapter):
    key = "linkedin"
    display_name = "LinkedIn Ads"


class TikTokAdsAdapter(StubAdapter):
    key = "tiktok"
    display_name = "TikTok Ads"


class MicrosoftAdsAdapter(StubAdapter):
    key = "microsoft"
    display_name = "Microsoft Advertising (Bing)"


class XAdsAdapter(StubAdapter):
    key = "x"
    display_name = "X Ads (Twitter)"


class RedditAdsAdapter(StubAdapter):
    key = "reddit"
    display_name = "Reddit Ads"
