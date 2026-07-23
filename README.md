# AdLift — AI Campaign Optimizer for B2B SaaS

An AI-powered platform that generates, measures, and improves paid acquisition
campaigns. Describe your product → the AI drafts audience, ad copy, and a
landing page → import performance data → get insights and one-click-ready
optimization suggestions. Humans stay in control (no auto-publishing in the MVP).

## Stack

- **Python 3.11**, managed with [uv](https://docs.astral.sh/uv/)
- **FastAPI** + Uvicorn (API + a self-contained web UI)
- **Pydantic** models throughout
- AI runs in **stub mode** by default — no API key needed to run the full flow.
  The brain is pluggable (`chat/brain.py`); swap in Claude later.

## Quickstart

```bash
uv sync                            # install deps into .venv
uv run gtm-paid-ai-distribution    # serves http://127.0.0.1:8000
```

- Web UI: <http://127.0.0.1:8000/>
- API docs (Swagger): <http://127.0.0.1:8000/docs>

Run the tests and linter:

```bash
uv run pytest
uv run ruff check .
```

## Domain model

```
Campaign            product, goal, budget, geography, audience (FR2)
  └── Experiment    an A/B arm: one channel + one message (FR3) + one landing page (FR4)
        └── Metrics imported performance for that arm (FR5)
```

Comparing a campaign's experiments *is* the A/B test (FR8); the best-performing
experiment is the "winning combination" (FR6).

## Website (sidebar navigation)

A single-page app served from `web/static/` with a sidebar:
Campaigns (list → detail) · New campaign (wizard) · Integrations · About.
Campaign detail shows the audience, its experiments, dashboard totals, insights,
and suggestions; experiment detail shows channel/message/landing page + metrics.

## How the code maps to the PRD

| PRD | Where |
|-----|-------|
| FR1 Campaign creation wizard | `questionnaire/` (data-driven `questions.yaml`) + `api/questionnaire.py` |
| FR2 Audience recommendation | `ai/generation.py:generate_audience` (campaign-level) |
| FR3 Creative / messaging | `ai/generation.py:generate_messages` (per experiment) |
| FR4 Landing page generation | `ai/generation.py:generate_landing_page` (per experiment) |
| FR5 Performance dashboard | `analytics/engine.py` + `/campaigns/{id}/analysis`, `/experiments/{id}/analysis` |
| FR6 AI insights / winning combo | `ai/insights.py:analyze_campaign` (rules engine) |
| FR7 Optimization suggestions | `ai/insights.py` |
| FR8 Experiment tracking (A/B) | `campaigns/models.py:Experiment` + `api/experiments.py` |
| Future: one-click publishing | `integrations/` (stub adapters: Google, Meta, LinkedIn, TikTok, MS, X, Reddit) |

## Customising the wizard

Edit `src/gtm_paid_ai_distribution/questionnaire/questions.yaml` — add/remove
questions and the API + UI follow automatically. Types: `text`, `number`,
`single_choice`, `multi_choice`, `boolean`.

## Google Ads (real integration)

Google Ads is wired end-to-end (the other platforms are stubs):

1. `uv sync --extra google` to install the `google-ads` client.
2. Set `GTM_GOOGLE_*` (see `.env.example`): developer token, OAuth client id/secret, customer id.
3. Connect an account: open `/integrations/google/oauth/start` → Google consent → the
   callback stores a refresh token. (Or set `GTM_GOOGLE_REFRESH_TOKEN` directly.)
4. Import real metrics onto an experiment: `POST /integrations/google/import`
   `{ "experiment_id": "...", "days": 7 }` — pulls campaign performance via GAQL.
5. Publish: `POST /integrations/google/publish`. **Safe by default** — it returns a
   dry-run unless `GTM_GOOGLE_ALLOW_PUBLISH=true`, and even then campaigns are created
   **PAUSED** so nothing spends money without review.

Going live requires a Google Ads **developer token** with API access (approval can take
days) and an OAuth client — see [developers.google.com/google-ads/api](https://developers.google.com/google-ads/api/docs/first-call/overview).

## Hosting

Two ready-to-go options (pick one):

**Render (recommended — persistent process).** `render.yaml` is a blueprint:
New → Blueprint → pick the repo → Apply. Runs a normal server, so in-memory data
persists while the instance is up (still resets on redeploy — add a DB for durability).

**Vercel (serverless).** `vercel.json` + `api/index.py` + `requirements.txt`:
`vercel --prod`. Ephemeral, so created data doesn't survive cold starts (seeded
examples always show); `google-ads` is excluded from the build.

For either, set secrets in the host's dashboard (never commit): `ANTHROPIC_API_KEY`,
`GTM_CHAT_BRAIN=claude` for real AI, and any `GTM_GOOGLE_*`.

## CI

`.github/workflows/ci.yml` runs ruff + pytest on every push to `main` and every PR
(via `uv sync` on Python 3.11).

> Secrets like `ANTHROPIC_API_KEY` and `GTM_GOOGLE_*` belong in a local `.env`
> (gitignored) or GitHub Actions secrets — never commit them.

## Roadmap (from the PRD)

Direct ad-platform publishing, AI image/video creatives, multi-armed-bandit
budget optimization, predictive lead scoring, cross-channel attribution,
and guardrailed agentic optimization.
