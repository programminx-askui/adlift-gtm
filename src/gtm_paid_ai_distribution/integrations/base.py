"""Shared contract for every ad-platform integration.

Each real platform (Google Ads, Meta, LinkedIn, ...) provides an adapter that
implements this interface. Today they are stubs; wire real OAuth + API calls
one adapter at a time without touching the rest of the app.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field


class ConnectionStatus(str, Enum):
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class Campaign(BaseModel):
    name: str
    objective: str
    daily_budget: float
    audience: str | None = None
    extra: dict[str, object] = Field(default_factory=dict)


class CampaignResult(BaseModel):
    platform: str
    external_id: str
    status: str
    detail: str | None = None


class AdPlatformAdapter(ABC):
    """Common surface every ad platform must expose."""

    #: Machine key, e.g. "google". Used in the registry and API routes.
    key: str
    #: Human-readable name, e.g. "Google Ads".
    display_name: str

    @abstractmethod
    def status(self) -> ConnectionStatus:
        """Report whether we currently have working credentials."""

    @abstractmethod
    def connect(self, credentials: dict[str, object]) -> ConnectionStatus:
        """Establish/refresh a connection (OAuth token exchange, etc.)."""

    @abstractmethod
    def create_campaign(self, campaign: Campaign) -> CampaignResult:
        """Create a campaign on the platform."""
