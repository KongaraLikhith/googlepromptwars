import asyncio
import json
import logging
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from app.ai import enrich_plan
from app.enrichment_cache import EnrichmentCache
from app.planner import build_plan
from app.schemas import PlanRequest


@pytest.fixture(autouse=True)
def isolated_enrichment_cache(monkeypatch):
    monkeypatch.setattr("app.ai._ENRICHMENTS", EnrichmentCache())


def sample():
    return PlanRequest(
        event_type="birthday",
        event_date=date.today() + timedelta(days=30),
        budget=10000,
        currency="INR",
        guest_count=20,
        preferences="Vegetarian food",
    )


def test_absent_key_never_constructs_network_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Key-free planning must never call a remote service")

    monkeypatch.setattr("app.ai.httpx.AsyncClient", forbidden)
    plan = asyncio.run(enrich_plan(sample(), build_plan(sample())))
    assert plan.source == "local"


def test_four_distinct_requests_are_bounded_and_busy_request_does_not_open_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    opened = 0
    started = asyncio.Event()
    release = asyncio.Event()
    valid = {
        "ideas": [{"title": "A shared activity", "description": "Offer seated choices."}] * 3,
        "tips": ["Confirm details.", "Keep labels clear.", "Use reusable supplies."],
    }

    async def handle(_request):
        nonlocal opened
        opened += 1
        if opened == 4:
            started.set()
        await release.wait()
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(valid)}]}}]}
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    async def exercise():
        requests = [sample().model_copy(update={"guest_count": count}) for count in range(1, 6)]
        active = [asyncio.create_task(enrich_plan(item, build_plan(item))) for item in requests[:4]]
        await started.wait()
        plan = await enrich_plan(requests[4], build_plan(requests[4]))
        assert plan.source == "local" and "busy" in plan.source_note
        assert len(plan.timeline) == 8 and len(plan.vendors) == 7
        assert opened == 4
        release.set()
        assert all(plan.source == "gemini" for plan in await asyncio.gather(*active))

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "model,expected_model,thinking_config",
    [
        (None, "gemini-3.5-flash-lite", None),
        ("gemini-3.8-flash", "gemini-3.8-flash", {"thinkingLevel": "low"}),
        ("gemini-2.5-flash-lite", "gemini-2.5-flash-lite", None),
        ("gemini-2.5-flash", "gemini-2.5-flash", {"thinkingBudget": 0}),
        ("custom-model", "custom-model", None),
    ],
)
def test_successful_gemini_changes_only_ideas_and_adds_tips(
    monkeypatch, model, expected_model, thinking_config
):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    if model is None:
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
    else:
        monkeypatch.setenv("GEMINI_MODEL", model)
    enrichment = {
        "ideas": [
            {"title": f"Personal idea {index}", "description": "A vegetarian picnic activity."}
            for index in range(3)
        ],
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
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(enrichment)}]}}]}
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
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
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": '{"ideas": []}'}]}}]}
        )

    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )
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
    valid = {
        "ideas": [{"title": "Recovered idea", "description": "A thoughtful idea."}] * 3,
        "tips": ["Keep it simple.", "Offer choices.", "Confirm details."],
    }

    def handle(request):
        if failing:
            if failure == "timeout":
                raise httpx.ReadTimeout("Upstream request timed out", request=request)
            return httpx.Response(429, json={"error": {"message": "Not returned to the user"}})
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(valid)}]}}]}
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

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


@pytest.mark.parametrize("failure", ["http-status", "timeout"])
def test_failure_diagnostics_exclude_credentials_private_text_and_errors(
    monkeypatch, caplog, failure
):
    key = "PRIVATE_KEY_MUST_NEVER_APPEAR"
    private_text = "PRIVATE_EVENT_PREFERENCES_MUST_NEVER_APPEAR"
    monkeypatch.setenv("GEMINI_API_KEY", key)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    request = sample().model_copy(update={"preferences": private_text})

    def handle(http_request):
        if failure == "timeout":
            raise httpx.ReadTimeout(private_text + key, request=http_request)
        return httpx.Response(429, json={"error": {"message": private_text + key}})

    real_client = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["timeout"].read == 45.0
        assert kwargs["timeout"].connect == 4.0
        return real_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr("app.ai.httpx.AsyncClient", client)
    with caplog.at_level(logging.WARNING, logger="app.ai"):
        result = asyncio.run(enrich_plan(request, build_plan(request)))
    assert result.source == "local"
    assert "model=gemini-3.5-flash-lite" in caplog.text
    assert "elapsed_s=" in caplog.text
    if failure == "http-status":
        assert "type=HTTPStatusError status=429" in caplog.text
    else:
        assert "type=ReadTimeout status=None" in caplog.text
    assert key not in caplog.text and private_text not in caplog.text
    assert "Traceback" not in caplog.text


def test_oversized_stream_is_closed_without_reading_remainder(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")

    class LargeStream(httpx.AsyncByteStream):
        chunks_read = 0
        closed = False

        async def __aiter__(self):
            for _ in range(100):
                self.chunks_read += 1
                yield b"x" * 4096

        async def aclose(self):
            self.closed = True

    stream = LargeStream()
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, stream=stream))
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    result = asyncio.run(enrich_plan(sample(), build_plan(sample())))
    assert result.source == "local" and "unavailable" in result.source_note
    assert stream.chunks_read == 9
    assert stream.closed


def test_excessively_nested_provider_json_uses_local_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    nested = b"[" * 2000 + b"0" + b"]" * 2000
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=nested))
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    result = asyncio.run(enrich_plan(sample(), build_plan(sample())))
    assert result.source == "local" and "unavailable" in result.source_note


def test_total_deadline_cancels_dribbling_stream_and_releases_model_capacity(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    monkeypatch.setattr("app.ai.MODEL_DEADLINE_SECONDS", 0.01)
    streams = []

    class SlowStream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self):
            while True:
                yield b" "
                await asyncio.sleep(0.005)

        async def aclose(self):
            self.closed = True

    def handle(_request):
        stream = SlowStream()
        streams.append(stream)
        return httpx.Response(200, stream=stream)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    async def exercise():
        for _ in range(5):
            result = await enrich_plan(sample(), build_plan(sample()))
            assert result.source == "local" and "unavailable" in result.source_note

    asyncio.run(exercise())
    assert len(streams) == 5 and all(stream.closed for stream in streams)


def test_success_cache_reuses_only_the_same_context_model_and_credential(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "first-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    calls = 0
    valid = {
        "ideas": [{"title": "An original idea", "description": "Offer seated activities."}] * 3,
        "tips": ["Confirm labels.", "Use reusable supplies.", "Offer choices."],
    }

    def handle(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(valid)}]}}]}
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        "app.ai.httpx.AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs),
    )

    async def exercise():
        request = sample().model_copy(update={"priorities": ["food", "decor"]})
        first = await enrich_plan(request, build_plan(request))
        first.ideas[0].title = "An edit must not mutate cached ideas"
        first.budget_items[0].amount = 123
        equivalent = request.model_copy(
            update={"budget": Decimal("10000.00"), "priorities": ["decor", "food"]}
        )
        second = await enrich_plan(equivalent, build_plan(equivalent))
        assert calls == 1
        assert second.source == "gemini" and second.ideas[0].title == "An original idea"
        assert second.budget_items[0].amount != 123
        changed = request.model_copy(update={"preferences": "A different planning preference"})
        await enrich_plan(changed, build_plan(changed))
        assert calls == 2
        monkeypatch.setenv("GEMINI_MODEL", "another-supported-model")
        await enrich_plan(request, build_plan(request))
        assert calls == 3
        monkeypatch.setenv("GEMINI_API_KEY", "rotated-test-key")
        await enrich_plan(request, build_plan(request))
        assert calls == 4

    asyncio.run(exercise())


def test_supplied_connection_pool_is_reused_and_not_closed_by_enrichment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-a-real-credential")
    calls = 0
    valid = {
        "ideas": [{"title": "A personalized idea", "description": "Offer a seated option."}] * 3,
        "tips": ["Confirm labels.", "Offer choices.", "Keep signs clear."],
    }

    def handle(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(valid)}]}}]}
        )

    real_client = httpx.AsyncClient

    def forbidden(**_kwargs):
        raise AssertionError("The application pool must be reused on distinct cache misses")

    monkeypatch.setattr("app.ai.httpx.AsyncClient", forbidden)

    async def exercise():
        async with real_client(transport=httpx.MockTransport(handle)) as client:
            for count in [20, 30]:
                request = sample().model_copy(update={"guest_count": count})
                result = await enrich_plan(request, build_plan(request), client=client)
                assert result.source == "gemini" and not client.is_closed
        assert client.is_closed and calls == 2

    asyncio.run(exercise())
