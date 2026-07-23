"""FastAPI application factory and entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import campaigns, chat, experiments, google, integrations, questionnaire
from .config import settings

STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0")

    if settings.seed_examples:
        from .campaigns.seed import seed_examples

        seed_examples()

    app.include_router(chat.router)
    app.include_router(questionnaire.router)
    app.include_router(campaigns.router)
    app.include_router(experiments.router)
    app.include_router(integrations.router)
    app.include_router(google.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "brain": settings.chat_brain}

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()


def main() -> None:
    """Console-script entry point (`gtm-paid-ai-distribution`)."""
    import uvicorn

    uvicorn.run(
        "gtm_paid_ai_distribution.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.debug,
    )
