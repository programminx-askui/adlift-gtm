"""Central registry of available ad-platform adapters."""

from __future__ import annotations

from .base import AdPlatformAdapter
from .google_ads_real import RealGoogleAdsAdapter
from .stub_adapter import (
    LinkedInAdsAdapter,
    MetaAdsAdapter,
    MicrosoftAdsAdapter,
    RedditAdsAdapter,
    TikTokAdsAdapter,
    XAdsAdapter,
)

# Google Ads is a real integration; the rest are stubs (Future publishing).
google_adapter = RealGoogleAdsAdapter()

_ADAPTERS: dict[str, AdPlatformAdapter] = {
    a.key: a
    for a in (
        google_adapter,
        MetaAdsAdapter(),
        LinkedInAdsAdapter(),
        TikTokAdsAdapter(),
        MicrosoftAdsAdapter(),
        XAdsAdapter(),
        RedditAdsAdapter(),
    )
}


def all_adapters() -> list[AdPlatformAdapter]:
    return list(_ADAPTERS.values())


def get_adapter(key: str) -> AdPlatformAdapter | None:
    return _ADAPTERS.get(key)
