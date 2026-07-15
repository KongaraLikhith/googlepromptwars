import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_election_events():
    response = client.get("/api/election-events")
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "events" in data
    assert len(data["events"]) >= 4
    
    # Check structure
    event = data["events"][0]
    assert "title" in event
    assert "description" in event
    assert "calendar_link" in event
    assert "google.com/calendar" in event["calendar_link"]
