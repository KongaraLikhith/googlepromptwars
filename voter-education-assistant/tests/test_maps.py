import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def test_polling_locations():
    with patch('routers.maps.find_polling_stations') as mock_find:
        mock_find.return_value = [
            {"name": "School Booth", "address": "123 Main St", "lat": 28.6, "lng": 77.2, "place_id": "123", "rating": 4.5}
        ]
        
        response = client.post("/api/polling-locations", json={
            "lat": 28.6139,
            "lng": 77.2090
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert len(data["locations"]) == 1
        assert data["locations"][0]["name"] == "School Booth"

def test_geocode_address():
    with patch('routers.maps.geocode_address') as mock_geocode:
        mock_geocode.return_value = {
            "lat": 28.6139,
            "lng": 77.2090,
            "formatted_address": "New Delhi, Delhi, India"
        }
        
        response = client.get("/api/geocode?address=New Delhi")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["result"]["lat"] == 28.6139

def test_geocode_non_india_address():
    with patch('routers.maps.geocode_address') as mock_geocode:
        mock_geocode.return_value = {
            "error": "Please enter a valid location or address within India."
        }
        
        response = client.get("/api/geocode?address=Texas")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert data["result"]["error"] == "Please enter a valid location or address within India."
