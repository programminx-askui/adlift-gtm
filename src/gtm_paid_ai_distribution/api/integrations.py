"""Ad-platform integration endpoints.

FUTURE (per PRD): one-click publishing to Google/LinkedIn/Meta/etc. All
adapters are stubs today; the MVP imports metrics via the dashboard instead.
Exposed now so the contract and UI can be built against it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..integrations.base import Campaign as PlatformCampaign
from ..integrations.base import CampaignResult, ConnectionStatus
from ..integrations.registry import all_adapters, get_adapter

router = APIRouter(prefix="/integrations", tags=["integrations (future)"])


class PlatformInfo(BaseModel):
    key: str
    display_name: str
    status: ConnectionStatus


@router.get("", response_model=list[PlatformInfo])
def list_platforms() -> list[PlatformInfo]:
    return [
        PlatformInfo(key=a.key, display_name=a.display_name, status=a.status())
        for a in all_adapters()
    ]


class ConnectRequest(BaseModel):
    credentials: dict[str, object] = {}


@router.post("/{key}/connect", response_model=PlatformInfo)
def connect(key: str, req: ConnectRequest) -> PlatformInfo:
    adapter = get_adapter(key)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Unknown platform {key!r}")
    status = adapter.connect(req.credentials)
    return PlatformInfo(key=adapter.key, display_name=adapter.display_name, status=status)


@router.post("/{key}/publish", response_model=CampaignResult)
def publish(key: str, campaign: PlatformCampaign) -> CampaignResult:
    adapter = get_adapter(key)
    if adapter is None:
        raise HTTPException(status_code=404, detail=f"Unknown platform {key!r}")
    return adapter.create_campaign(campaign)
