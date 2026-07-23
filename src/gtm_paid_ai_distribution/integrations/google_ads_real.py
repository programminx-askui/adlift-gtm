"""Real Google Ads integration.

End-to-end path: OAuth (authorization-code flow) → connect → import performance
metrics (GAQL) → optionally publish a campaign. It degrades gracefully:

  - Credentials resolve from env (``GTM_GOOGLE_*``) and can be updated at runtime
    (e.g. an OAuth callback sets the refresh token).
  - If the ``google-ads`` library isn't installed or creds are missing,
    ``status()`` reports why instead of raising.
  - Publishing is OFF by default (``settings.google_allow_publish``); even when
    enabled, campaigns are created **PAUSED** so nothing spends money unreviewed.

The heavy ``google-ads`` dependency is imported lazily, so importing this module
(and running the rest of the app / tests) never requires it.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from functools import lru_cache

from ..campaigns.models import MetricsSnapshot
from ..config import settings
from .base import (
    AdPlatformAdapter,
    Campaign,
    CampaignResult,
    ConnectionStatus,
)

logger = logging.getLogger(__name__)

_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
_SCOPE = "https://www.googleapis.com/auth/adwords"
_API_VERSION = "v18"


class GoogleAdsCredentials:
    """Runtime-mutable credential holder, seeded from settings/env."""

    def __init__(self) -> None:
        self.developer_token = settings.google_developer_token
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.refresh_token = settings.google_refresh_token
        self.login_customer_id = settings.google_login_customer_id
        self.customer_id = settings.google_customer_id

    def update(self, values: dict[str, object]) -> None:
        for key in vars(self):
            if key in values and values[key]:
                setattr(self, key, str(values[key]))

    @property
    def complete(self) -> bool:
        return all(
            [
                self.developer_token,
                self.client_id,
                self.client_secret,
                self.refresh_token,
                self.customer_id,
            ]
        )

    def to_client_config(self) -> dict[str, object]:
        cfg: dict[str, object] = {
            "developer_token": self.developer_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "use_proto_plus": True,
        }
        if self.login_customer_id:
            cfg["login_customer_id"] = self.login_customer_id
        return cfg


@lru_cache(maxsize=1)
def library_available() -> bool:
    try:
        import google.ads.googleads.client  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 — optional dependency
        return False


def build_authorization_url(state: str = "adlift") -> str:
    """Step 1 of OAuth: the consent-screen URL the user visits."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": _SCOPE,
        "access_type": "offline",
        "prompt": "consent",  # force a refresh_token every time
        "state": state,
    }
    return f"{_OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, object]:
    """Step 2 of OAuth: exchange the authorization code for tokens.

    Uses the stdlib (no extra dependency) to POST to Google's token endpoint.
    """
    data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310 — fixed https endpoint
        _OAUTH_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


class RealGoogleAdsAdapter(AdPlatformAdapter):
    key = "google"
    display_name = "Google Ads"

    def __init__(self, credentials: GoogleAdsCredentials | None = None) -> None:
        self.creds = credentials or GoogleAdsCredentials()

    # --- connection ------------------------------------------------------
    def status(self) -> ConnectionStatus:
        if not library_available():
            return ConnectionStatus.error  # library not installed
        return ConnectionStatus.connected if self.creds.complete else ConnectionStatus.disconnected

    def status_detail(self) -> str:
        if not library_available():
            return "google-ads library not installed (uv sync --extra google)"
        if not self.creds.complete:
            missing = [
                k
                for k in ("developer_token", "client_id", "client_secret", "refresh_token", "customer_id")
                if not getattr(self.creds, k)
            ]
            return f"missing credentials: {', '.join(missing)}"
        return "connected"

    def connect(self, credentials: dict[str, object]) -> ConnectionStatus:
        self.creds.update(credentials)
        return self.status()

    def _client(self):
        from google.ads.googleads.client import GoogleAdsClient

        return GoogleAdsClient.load_from_dict(self.creds.to_client_config(), version=_API_VERSION)

    # --- metrics import (read) ------------------------------------------
    def fetch_metrics(self, days: int = 7, customer_id: str | None = None) -> list[MetricsSnapshot]:
        """FR5 — pull recent campaign performance and map to MetricsSnapshots."""
        cid = (customer_id or self.creds.customer_id or "").replace("-", "")
        if not self.creds.complete or not cid:
            raise RuntimeError(self.status_detail())

        client = self._client()
        service = client.get_service("GoogleAdsService")
        query = (
            "SELECT campaign.id, campaign.name, metrics.impressions, metrics.clicks, "
            "metrics.conversions, metrics.cost_micros, metrics.conversions_value "
            "FROM campaign "
            f"WHERE segments.date DURING LAST_{int(days)}_DAYS"
        )
        snapshots: list[MetricsSnapshot] = []
        for row in service.search(customer_id=cid, query=query):
            m = row.metrics
            snapshots.append(
                MetricsSnapshot(
                    impressions=int(m.impressions),
                    clicks=int(m.clicks),
                    conversions=int(m.conversions),
                    spend=round(m.cost_micros / 1_000_000, 2),
                    revenue=round(float(m.conversions_value), 2),
                )
            )
        return snapshots

    # --- publish (write) — safe by default ------------------------------
    def create_campaign(self, campaign: Campaign) -> CampaignResult:
        """Publish a campaign. Gated + always PAUSED so it never auto-spends.

        Returns a dry-run result unless ``settings.google_allow_publish`` is
        true and credentials are complete.
        """
        if not settings.google_allow_publish:
            return CampaignResult(
                platform=self.key,
                external_id="dry-run",
                status="dry_run",
                detail=(
                    f"Would create PAUSED campaign {campaign.name!r} "
                    f"(daily budget ${campaign.daily_budget}). Set "
                    "GTM_GOOGLE_ALLOW_PUBLISH=true to publish for real."
                ),
            )
        if not self.creds.complete:
            return CampaignResult(
                platform=self.key, external_id="error", status="error",
                detail=self.status_detail(),
            )
        return self._publish_paused(campaign)

    def _publish_paused(self, campaign: Campaign) -> CampaignResult:
        cid = self.creds.customer_id.replace("-", "")
        client = self._client()

        # 1) budget
        budget_service = client.get_service("CampaignBudgetService")
        budget_op = client.get_type("CampaignBudgetOperation")
        budget = budget_op.create
        budget.name = f"{campaign.name} budget"
        budget.amount_micros = int(max(campaign.daily_budget, 1) * 1_000_000)
        budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        budget_res = budget_service.mutate_campaign_budgets(
            customer_id=cid, operations=[budget_op]
        )
        budget_resource = budget_res.results[0].resource_name

        # 2) campaign — created PAUSED (never auto-spends)
        campaign_service = client.get_service("CampaignService")
        campaign_op = client.get_type("CampaignOperation")
        c = campaign_op.create
        c.name = campaign.name
        c.status = client.enums.CampaignStatusEnum.PAUSED
        c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
        c.manual_cpc = client.get_type("ManualCpc")
        c.campaign_budget = budget_resource
        result = campaign_service.mutate_campaigns(customer_id=cid, operations=[campaign_op])
        resource_name = result.results[0].resource_name
        return CampaignResult(
            platform=self.key,
            external_id=resource_name,
            status="created_paused",
            detail=f"Created PAUSED campaign {campaign.name!r} — review before enabling.",
        )
