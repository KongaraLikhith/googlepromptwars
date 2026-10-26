import asyncio
from datetime import date, timedelta
import json

import httpx
import pytest

from app.ai import enrich_plan
from app.planner import build_plan
from app.schemas import PlanRequest


def sample():
    return PlanRequest(event_type="birthday", event_date=date.today() + timedelta(days=30),
                       budget=10000, currency="INR", guest_count=20, preferences="Vegetarian food")


def test_absent_key_never_constructs_network_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Key-free planning must never call a remote service")
    monkeypatch.setattr("app.ai.httpx.AsyncClient", forbidden)
    plan = asyncio.run(enrich_plan(sample(), build_plan(sample())))
    assert plan.source == "local"


@pytest.mark.parametrize("model,expected_model,thinking_config", [
    (None, "gemini-3.5-flash-lite", None),
    ("gemini-3.8-flash", "gemini-3.8-flash", {"thinkingLevel": "low"}),
    ("gemini-2.5-flash-lite", "gemini-2.5-flash-lite", None),
    ("gemini-2.5-flash", "gemini-2.5-flash", {"thinkingBudget": 0}),
    ("custom-model", "custom-model", None),
])
def test_successful_gemini_changes_only_ideas_and_adds_tips(monkeypatch, model, expected_model, thinking_config):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    if model is None:
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
    else:
        monkeypatch.setenv("GEMINI_MODEL", model)
    enrichment = {
        "ideas": [{"title": f"Personal idea {index}", "description": "A vegetarian picnic activity."} for index in range(3)],
        "tips": ["Confirm dietary labels.", "Use reusable tableware.", "Offer seated activities."],
    }
    def handle(request):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.path == f"/v1beta/models/{expected_model}:generateContent"
        assert request.headers["x-goog-api-key"] == "test-key-not-a-real-credential"
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert body["generationConfig"]["maxOutputTokens"] == 2500
        if thinking_config is None:
            assert "thinkingConfig" not in body["generationConfig"]
        else:
            assert body["generationConfig"]["thinkingConfig"] == thinking_config
        assert "untrusted user data" in body["contents"][0]["parts"][0]["text"]
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(enrichment)}]}}]})
    real_client = httpx.AsyncClient
    monkeypatch.setattr("app.ai.httpx.AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    original = build_plan(sample())
    before = original.model_dump()
    result = asyncio.run(enrich_plan(sample(), original))
    assert result.source == "gemini" and result.ideas[0].title == "Personal idea 0"
    for field in ["budget_items", "timeline", "vendors", "budget", "per_guest"]:
        assert result.model_dump()[field] == before[field]
    assert result.tips[:3] == before["tips"][:3]


def test_malformed_or_failed_model_response_uses_honest_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    real_client = httpx.AsyncClient
    def handle(request):
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"ideas": []}'}]}}]})
    monkeypatch.setattr("app.ai.httpx.AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    original = build_plan(sample())
    before = original.model_dump()
    result = asyncio.run(enrich_plan(sample(), original))
    assert result.source == "local" and "unavailable" in result.source_note
    assert result.model_dump()["ideas"] == before["ideas"]
    assert result.model_dump()["budget_items"] == before["budget_items"]


def test_invalid_model_configuration_does_not_make_network_request(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setenv("GEMINI_MODEL", "../unexpected/route")
    result = asyncio.run(enrich_plan(sample(), build_plan(sample())))
    assert result.source == "local" and "not configured" in result.source_note


@pytest.mark.parametrize("failure", ["timeout", "rate-limit"])
def test_upstream_failures_fall_back_and_capacity_recovers(monkeypatch, failure):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    failing = True
    valid = {"ideas": [{"title": "Recovered idea", "description": "A thoughtful idea."}] * 3,
             "tips": ["Keep it simple.", "Offer choices.", "Confirm details."]}
    def handle(request):
        if failing:
            if failure == "timeout":
                raise httpx.ReadTimeout("Upstream request timed out", request=request)
            return httpx.Response(429, json={"error": {"message": "Not returned to the user"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(valid)}]}}]})
    real_client = httpx.AsyncClient
    monkeypatch.setattr("app.ai.httpx.AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))

    async def exercise():
        nonlocal failing
        # Repeated failures must not exhaust the four model-request slots.
        for _ in range(4):
            fallback = await enrich_plan(sample(), build_plan(sample()))
            assert fallback.source == "local" and "unavailable" in fallback.source_note
            assert "Not returned" not in fallback.source_note
        failing = False
        recovered = await enrich_plan(sample(), build_plan(sample()))
        assert recovered.source == "gemini"
    asyncio.run(exercise())
