"""Google Ads integration endpoints: OAuth, status, metrics import, publish.

This is the one real ad-platform integration (the rest are stubs). Publishing
is safe-by-default — see `integrations.google_ads_real`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from ..campaigns.service import service as campaign_service
from ..config import settings
from ..integrations import google_ads_real as g
from ..integrations.base import Campaign as PlatformCampaign
from ..integrations.base import CampaignResult
from ..integrations.registry import google_adapter

router = APIRouter(prefix="/integrations/google", tags=["google ads"])


class GoogleStatus(BaseModel):
    connected: bool
    detail: str
    oauth_ready: bool
    library_installed: bool
    publish_enabled: bool


@router.get("/status", response_model=GoogleStatus)
def status() -> GoogleStatus:
    return GoogleStatus(
        connected=google_adapter.creds.complete and g.library_available(),
        detail=google_adapter.status_detail(),
        oauth_ready=settings.google_oauth_ready,
        library_installed=g.library_available(),
        publish_enabled=settings.google_allow_publish,
    )


@router.get("/oauth/start")
def oauth_start() -> RedirectResponse:
    """Redirect the user to Google's consent screen."""
    if not settings.google_oauth_ready:
        raise HTTPException(
            status_code=400,
            detail="Set GTM_GOOGLE_CLIENT_ID and GTM_GOOGLE_CLIENT_SECRET first.",
        )
    return RedirectResponse(g.build_authorization_url())


@router.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback(
    code: str | None = Query(default=None), error: str | None = Query(default=None)
) -> HTMLResponse:
    """Exchange the authorization code for a refresh token and store it."""
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    try:
        tokens = g.exchange_code_for_tokens(code)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {exc}") from exc

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh_token returned (revoke prior grant and retry).",
        )
    google_adapter.connect({"refresh_token": refresh_token})
    return HTMLResponse(
        "<h2>✅ Google Ads connected</h2>"
        "<p>Refresh token stored for this session. You can close this tab.</p>"
        "<p><a href='/#/integrations'>Back to AdLift</a></p>"
    )


class ImportRequest(BaseModel):
    experiment_id: str
    days: int = 7
    customer_id: str | None = None


@router.post("/import")
def import_metrics(req: ImportRequest) -> dict[str, object]:
    """FR5 — pull real Google Ads metrics and attach them to an experiment."""
    if campaign_service.find_experiment(req.experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    try:
        snapshots = google_adapter.fetch_metrics(days=req.days, customer_id=req.customer_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    campaign_service.import_metrics(req.experiment_id, snapshots)
    return {"experiment_id": req.experiment_id, "snapshots_imported": len(snapshots)}


@router.post("/publish", response_model=CampaignResult)
def publish(campaign: PlatformCampaign) -> CampaignResult:
    """Create a PAUSED campaign on Google Ads (dry-run unless publishing enabled)."""
    return google_adapter.create_campaign(campaign)
