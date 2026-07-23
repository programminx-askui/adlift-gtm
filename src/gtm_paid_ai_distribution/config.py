"""Application configuration, loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """Runtime settings. Override any field via env vars (see .env.example)."""

    model_config = SettingsConfigDict(
        env_prefix="GTM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AdLift — AI Campaign Optimizer"
    debug: bool = True
    # Seed example campaigns on startup (when the store is empty).
    seed_examples: bool = True

    # Chatbot / generation brain: "stub" (no key needed) or "claude" (real LLM).
    chat_brain: str = "stub"
    # Anthropic model id used when chat_brain == "claude".
    anthropic_model: str = "claude-opus-4-8"

    # Path to the data-driven questionnaire definition.
    questionnaire_path: Path = PACKAGE_DIR / "questionnaire" / "questions.yaml"

    # --- Google Ads (real integration; all optional) ---------------------
    google_developer_token: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_login_customer_id: str = ""  # MCC id (digits only), optional
    google_customer_id: str = ""  # target account id (digits only)
    google_redirect_uri: str = "http://127.0.0.1:8000/integrations/google/oauth/callback"
    # SAFETY: publishing real campaigns is OFF by default. Even when enabled,
    # campaigns are created PAUSED so nothing spends money without review.
    google_allow_publish: bool = False

    @property
    def use_llm(self) -> bool:
        """Whether AI generation/chat should call a real LLM."""
        return self.chat_brain == "claude"

    @property
    def google_oauth_ready(self) -> bool:
        """Whether an OAuth client is configured (enough to start the flow)."""
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
