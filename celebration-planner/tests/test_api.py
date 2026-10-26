from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import SlidingWindowRateLimiter

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_live_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(app.state, "plan_limiter", SlidingWindowRateLimiter())


def payload(**changes):
    values = {
        "event_type": "community",
        "event_date": (date.today() + timedelta(days=90)).isoformat(),
        "budget": 50000,
        "currency": "INR",
        "guest_count": 100,
        "style": "Neighborhood picnic",
        "priorities": ["food", "accessibility"],
    }
    return values | changes


def test_complete_plan_endpoint_and_health_without_google_credentials():
    response = client.post("/api/plan", json=payload())
    assert response.status_code == 200
    plan = response.json()
    assert plan["source"] == "local"
    assert plan["guest_count"] == 100 and plan["per_guest"] == 500
    assert len(plan["budget_items"]) == 7 and len(plan["timeline"]) == 8
    assert len(plan["vendors"]) == 7 and len(plan["ideas"]) == 3
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/health").json()["service"] == "Gatherly"


@pytest.mark.parametrize(
    "changes",
    [
        {"budget": -1},
        {"budget": "100.001"},
        {"budget": 100000001},
        {"guest_count": 0},
        {"guest_count": 10001},
        {"guest_count": 1.5},
        {"guest_count": True},
        {"event_type": "conference"},
        {"currency": "ZZZ"},
        {"location": "x" * 101},
        {"priorities": ["food", "food"]},
        {"priorities": ["food", "decor", "venue", "photography"]},
        {"event_date": (date.today() - timedelta(days=1)).isoformat()},
        {"event_date": (date.today() + timedelta(days=731)).isoformat()},
        {"preferences": "x" * 501},
        {"secret": "unexpected extra input"},
    ],
)
def test_invalid_inputs_are_rejected(changes):
    response = client.post("/api/plan", json=payload(**changes))
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize("special_number", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_budget_returns_validation_error_without_server_crash(special_number):
    import json

    raw = json.dumps(payload()).replace('"budget": 50000', f'"budget": {special_number}')
    response = client.post("/api/plan", content=raw, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"]


def test_body_limit_applies_even_without_a_content_length():
    response = client.post("/api/plan", content=(chunk for chunk in [b"x" * 5000, b"y" * 5000]))
    assert response.status_code == 413
    assert response.json()["detail"] == "Request is too large."


def test_security_headers_and_validation_do_not_echo_notes():
    response = client.post("/api/plan", json=payload(preferences="private note" * 100))
    assert response.status_code == 422
    assert "private note" not in response.text
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "object-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Cross-Origin-Resource-Policy"] == "same-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert response.headers["Cache-Control"] == "no-store"


def test_static_root_is_independent_of_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert "Gatherly" in response.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/../main.py").status_code == 404


def test_rate_limit_rejects_excess_valid_plans_and_ignores_spoofed_forwarded_headers():
    for index in range(12):
        response = client.post(
            "/api/plan", json=payload(), headers={"X-Forwarded-For": f"192.0.2.{index}"}
        )
        assert response.status_code == 200
    response = client.post("/api/plan", json=payload(), headers={"X-Forwarded-For": "198.51.100.1"})
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 600
    assert "wait" in response.json()["detail"]
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_invalid_inputs_do_not_consume_plan_quota():
    for _ in range(13):
        assert client.post("/api/plan", json=payload(guest_count=0)).status_code == 422
    assert client.post("/api/plan", json=payload()).status_code == 200
