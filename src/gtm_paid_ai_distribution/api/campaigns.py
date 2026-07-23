"""Campaign endpoints: create (FR1), read, edit, list/create experiments, analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..ai.advisor import AiRecommendations, ai_recommendations
from ..ai.insights import CampaignAnalysis, analyze_campaign
from ..campaigns.models import (
    Audience,
    Campaign,
    CampaignGoal,
    CampaignStatus,
    Channel,
    Experiment,
)
from ..campaigns.service import service
from ..config import settings

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CreateCampaignRequest(BaseModel):
    product_description: str
    goal: CampaignGoal = CampaignGoal.leads
    monthly_budget: float = 0.0
    geography: str = ""
    generate: bool = True


class UpdateCampaignRequest(BaseModel):
    goal: CampaignGoal | None = None
    monthly_budget: float | None = None
    geography: str | None = None
    status: CampaignStatus | None = None
    audience: Audience | None = None


@router.post("", response_model=Campaign, status_code=201)
def create_campaign(req: CreateCampaignRequest) -> Campaign:
    return service.create(
        product_description=req.product_description,
        goal=req.goal,
        monthly_budget=req.monthly_budget,
        geography=req.geography,
        generate=req.generate,
    )


@router.get("", response_model=list[Campaign])
def list_campaigns() -> list[Campaign]:
    return service.repo.list()


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(campaign_id: str) -> Campaign:
    campaign = service.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=Campaign)
def update_campaign(campaign_id: str, req: UpdateCampaignRequest) -> Campaign:
    # Keep nested model instances (not dicts) so model_copy stores real models.
    changes = {k: v for k, v in vars(req).items() if v is not None}
    campaign = service.update(campaign_id, changes)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/analysis", response_model=CampaignAnalysis)
def campaign_analysis(campaign_id: str) -> CampaignAnalysis:
    """FR5/FR6/FR7 — totals, per-experiment metrics, insights, suggestions."""
    campaign = service.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return analyze_campaign(campaign)


@router.post("/{campaign_id}/ai-analysis", response_model=AiRecommendations)
def campaign_ai_analysis(campaign_id: str) -> AiRecommendations:
    """AI-written improvement recommendations for the campaign (via Claude)."""
    campaign = service.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not settings.use_llm:
        raise HTTPException(
            status_code=400,
            detail="AI analysis needs Claude — set GTM_CHAT_BRAIN=claude and ANTHROPIC_API_KEY.",
        )
    try:
        return ai_recommendations(campaign)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Claude analysis failed: {exc}") from exc


# --- Experiments nested under a campaign ---------------------------------
@router.get("/{campaign_id}/experiments", response_model=list[Experiment])
def list_experiments(campaign_id: str) -> list[Experiment]:
    campaign = service.get(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign.experiments


class CreateExperimentRequest(BaseModel):
    channel: Channel = Channel.linkedin
    generate: bool = True
    experiment: Experiment | None = None  # supply to add a fully-specified arm


@router.post("/{campaign_id}/experiments", response_model=Experiment, status_code=201)
def create_experiment(campaign_id: str, req: CreateExperimentRequest) -> Experiment:
    if req.generate and req.experiment is None:
        exp = service.generate_experiment(campaign_id, req.channel)
    else:
        exp = service.add_experiment(
            campaign_id, req.experiment or Experiment(channel=req.channel)
        )
    if exp is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return exp
