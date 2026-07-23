"""End-to-end and unit tests for the AI Campaign Optimizer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from gtm_paid_ai_distribution.analytics.engine import derive
from gtm_paid_ai_distribution.campaigns.models import MetricsSnapshot
from gtm_paid_ai_distribution.main import create_app

client = TestClient(create_app())


def _new_campaign(desc: str = "We help SDR teams automate account research."):
    return client.post(
        "/campaigns",
        json={"product_description": desc, "goal": "leads",
              "monthly_budget": 5000, "geography": "US"},
    ).json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analytics_derived_rates():
    m = derive(
        MetricsSnapshot(impressions=1000, clicks=50, conversions=5, spend=100, revenue=300)
    )
    assert m.ctr == 0.05
    assert m.cpc == 2.0
    assert m.cpa == 20.0
    assert m.conversion_rate == 0.1
    assert m.roas == 3.0


def test_analytics_handles_zero_division():
    m = derive(MetricsSnapshot())
    assert m.ctr == 0.0 and m.cpc == 0.0 and m.roas == 0.0


def test_create_campaign_generates_audience_and_experiments():
    c = _new_campaign()
    assert c["audience"] is not None
    assert len(c["experiments"]) >= 2  # seeded A/B arms
    exp = c["experiments"][0]
    assert exp["message"]["headline"]
    assert exp["landing_page"]["hero"]
    assert exp["channel"] in {
        "google", "linkedin", "meta", "tiktok", "microsoft", "x", "reddit"
    }


def test_add_and_patch_experiment():
    c = _new_campaign()
    # Add a generated experiment on a specific channel.
    exp = client.post(
        f"/campaigns/{c['id']}/experiments",
        json={"channel": "google", "generate": True},
    ).json()
    assert exp["channel"] == "google"

    # Patch its status to "winner".
    patched = client.patch(
        f"/experiments/{exp['id']}", json={"status": "winner"}
    ).json()
    assert patched["status"] == "winner"


def test_metrics_import_and_campaign_analysis_picks_winner():
    c = _new_campaign("AI SDR platform")
    a, b = c["experiments"][0], c["experiments"][1]

    # A converts well (low CPA); B converts poorly (high CPA).
    client.post(f"/experiments/{a['id']}/metrics", json={"snapshots": [
        {"impressions": 12000, "clicks": 372, "conversions": 22,
         "spend": 1900, "revenue": 4200}]})
    client.post(f"/experiments/{b['id']}/metrics", json={"snapshots": [
        {"impressions": 9000, "clicks": 210, "conversions": 6,
         "spend": 1500, "revenue": 900}]})

    analysis = client.get(f"/campaigns/{c['id']}/analysis").json()
    assert analysis["totals"]["impressions"] == 21000
    assert len(analysis["experiments"]) >= 2
    actions = {s["action"] for s in analysis["suggestions"]}
    assert "scale_experiment" in actions
    assert "pause_experiment" in actions


def test_experiment_level_analysis():
    c = _new_campaign()
    exp = c["experiments"][0]
    client.post(f"/experiments/{exp['id']}/metrics", json={"snapshots": [
        {"impressions": 1000, "clicks": 50, "conversions": 5,
         "spend": 100, "revenue": 300}]})
    m = client.get(f"/experiments/{exp['id']}/analysis").json()
    assert m["ctr"] == 0.05 and m["roas"] == 3.0


def test_questionnaire_wizard_creates_campaign_with_experiments():
    session_id = client.post("/questionnaire/start").json()["session_id"]
    data = None
    for ans in ["We help SDR teams automate research.", "leads", "5000", "US"]:
        data = client.post(
            "/questionnaire/answer",
            json={"session_id": session_id, "answer": ans},
        ).json()
    assert data["complete"] is True
    assert data["campaign"]["audience"] is not None
    assert len(data["campaign"]["experiments"]) >= 2


def test_landing_page_renders_html():
    c = _new_campaign()
    exp = c["experiments"][0]
    r = client.get(f"/experiments/{exp['id']}/landing")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "<!doctype html>" in body.lower()
    assert exp["message"]["headline"] in body


def test_ab_landing_pages_look_different():
    # Variant A and Variant B must render with distinct visual themes.
    c = _new_campaign()
    a, b = c["experiments"][0], c["experiments"][1]
    body_a = client.get(f"/experiments/{a['id']}/landing").text
    body_b = client.get(f"/experiments/{b['id']}/landing").text
    theme_a = body_a.split('data-theme="', 1)[1].split('"', 1)[0]
    theme_b = body_b.split('data-theme="', 1)[1].split('"', 1)[0]
    assert theme_a != theme_b


def test_integrations_listed_as_stubs():
    keys = {p["key"] for p in client.get("/integrations").json()}
    assert {"google", "meta", "linkedin"}.issubset(keys)


def test_example_campaigns_are_seeded():
    campaigns = client.get("/campaigns").json()
    descriptions = [c["product_description"] for c in campaigns]
    assert any("SDR" in d for d in descriptions)
    # The seeded SDR campaign has metrics → analysis should name a winner.
    sdr = next(c for c in campaigns if "SDR" in c["product_description"])
    analysis = client.get(f"/campaigns/{sdr['id']}/analysis").json()
    actions = {s["action"] for s in analysis["suggestions"]}
    assert "scale_experiment" in actions


def test_google_status_reports_not_configured():
    s = client.get("/integrations/google/status").json()
    assert s["connected"] is False
    assert s["publish_enabled"] is False  # safe by default
    assert "connected" not in s["detail"] or s["library_installed"] is False


def test_google_oauth_start_requires_client_config():
    # No client id/secret configured in tests → 400, not a redirect.
    r = client.get("/integrations/google/oauth/start", follow_redirects=False)
    assert r.status_code == 400


def test_google_authorization_url_includes_params(monkeypatch):
    from gtm_paid_ai_distribution.config import settings
    from gtm_paid_ai_distribution.integrations import google_ads_real as g

    monkeypatch.setattr(settings, "google_client_id", "client-123")
    url = g.build_authorization_url(state="s1")
    assert "accounts.google.com" in url
    assert "client_id=client-123" in url
    assert "access_type=offline" in url and "state=s1" in url


def test_google_publish_is_dry_run_by_default():
    r = client.post(
        "/integrations/google/publish",
        json={"name": "Test", "objective": "leads", "daily_budget": 50},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "dry_run"


def test_google_import_unknown_experiment_404():
    r = client.post(
        "/integrations/google/import",
        json={"experiment_id": "nope", "days": 7},
    )
    assert r.status_code == 404


def test_brain_factory_resolves_both_without_api_key():
    # ClaudeBrain must construct without any credentials (client is lazy);
    # only calling reply() would touch the network.
    from gtm_paid_ai_distribution.chat.brain import ClaudeBrain, StubBrain, get_brain

    assert isinstance(get_brain("stub"), StubBrain)
    assert isinstance(get_brain("claude"), ClaudeBrain)


def test_stub_generation_is_default():
    # With the default stub brain, generation runs with no external calls.
    from gtm_paid_ai_distribution.config import settings

    assert settings.use_llm is False
    c = _new_campaign()
    assert c["experiments"][0]["message"]["headline"]
