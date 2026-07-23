"""Experiment endpoints: read, edit, import metrics (FR5), per-arm analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..analytics.engine import DerivedMetrics
from ..ai.insights import analyze_experiment
from ..campaigns.models import (
    Channel,
    Experiment,
    ExperimentStatus,
    LandingPage,
    MarketingMessage,
    MetricsSnapshot,
)
from ..campaigns.service import service
from ..web.landing import render_landing_page

router = APIRouter(prefix="/experiments", tags=["experiments"])


class UpdateExperimentRequest(BaseModel):
    name: str | None = None
    channel: Channel | None = None
    status: ExperimentStatus | None = None
    message: MarketingMessage | None = None
    landing_page: LandingPage | None = None


class ImportMetricsRequest(BaseModel):
    snapshots: list[MetricsSnapshot]


@router.get("/{experiment_id}", response_model=Experiment)
def get_experiment(experiment_id: str) -> Experiment:
    found = service.find_experiment(experiment_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return found[1]


@router.patch("/{experiment_id}", response_model=Experiment)
def update_experiment(experiment_id: str, req: UpdateExperimentRequest) -> Experiment:
    # Keep nested model instances (not dicts) so model_copy stores real models.
    changes = {k: v for k, v in vars(req).items() if v is not None}
    exp = service.update_experiment(experiment_id, changes)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.post("/{experiment_id}/metrics", response_model=Experiment)
def import_metrics(experiment_id: str, req: ImportMetricsRequest) -> Experiment:
    """FR5 — import performance data for this experiment."""
    exp = service.import_metrics(experiment_id, req.snapshots)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.get("/{experiment_id}/analysis", response_model=DerivedMetrics)
def experiment_analysis(experiment_id: str) -> DerivedMetrics:
    found = service.find_experiment(experiment_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return analyze_experiment(found[1])


@router.get("/{experiment_id}/landing", response_class=HTMLResponse)
def landing_page(experiment_id: str) -> HTMLResponse:
    """FR4 — the real, responsive landing page a visitor would see."""
    found = service.find_experiment(experiment_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return HTMLResponse(render_landing_page(found[1]))
