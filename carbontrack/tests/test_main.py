import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_get_insights():
    with patch("app.main.get_insights", new_callable=AsyncMock) as mock:
        mock.return_value = "Mocked insights: **Eat more plants!**"
        yield mock


@pytest.fixture
def mock_get_chat_response():
    with patch("app.main.get_chat_response", new_callable=AsyncMock) as mock:
        mock.return_value = "Mocked chat response: Hello!"
        yield mock


def test_read_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_calculate_and_get_insights(mock_get_insights):
    payload = {
        "transport_miles_per_week": 100,
        "mpg": 25,
        "electricity_kwh_per_month": 500,
        "diet_type": "omnivore",
    }
    response = client.post("/api/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "footprint" in data
    assert "insights" in data
    assert data["footprint"]["total_co2_lbs"] > 0
    assert data["insights"] == "Mocked insights: **Eat more plants!**"
    mock_get_insights.assert_called_once()


@pytest.mark.asyncio
async def test_chat_with_assistant(mock_get_chat_response):
    payload = {"message": "Hi there", "history": []}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"] == "Mocked chat response: Hello!"
    mock_get_chat_response.assert_called_once()


def test_security_headers():
    response = client.get("/")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")
