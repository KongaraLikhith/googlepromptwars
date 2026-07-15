import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def test_chat_valid_message():
    with patch('routers.chat.get_gemini_response') as mock_gemini:
        mock_gemini.return_value = "This is a mocked response about elections."
        
        response = client.post("/api/chat", json={
            "message": "What is EVM?",
            "history": []
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["response"] == "This is a mocked response about elections."

def test_chat_empty_message():
    response = client.post("/api/chat", json={
        "history": []
        # Missing 'message'
    })
    
    assert response.status_code == 422 # Pydantic validation error
