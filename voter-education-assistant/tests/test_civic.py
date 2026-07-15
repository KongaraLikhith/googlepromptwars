import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def test_elections():
    with patch('routers.civic.get_elections') as mock_elections:
        mock_elections.return_value = {
            "elections": [{"id": "2000", "name": "VIP Test Election", "electionDay": "2024-06-01"}]
        }
        
        response = client.get("/api/elections?address=Delhi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["elections"]) == 1

def test_voter_info():
    with patch('routers.civic.get_voter_info') as mock_voter_info:
        mock_voter_info.return_value = {
            "pollingLocations": [{"address": {"locationName": "Test School", "city": "Delhi"}}],
            "state": [{"name": "Delhi"}]
        }
        
        response = client.get("/api/voter-info?address=Delhi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["polling_locations"]) == 1

def test_representatives():
    with patch('routers.civic.get_representatives') as mock_reps:
        mock_reps.return_value = {
            "offices": [{"name": "Mayor"}],
            "officials": [{"name": "John Doe"}]
        }
        
        response = client.get("/api/representatives?address=Delhi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["offices"]) == 1
