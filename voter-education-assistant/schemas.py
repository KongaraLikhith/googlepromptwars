from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    """Schema for chat endpoint request."""
    message: str
    history: List[Dict[str, str]] = []

class LocationRequest(BaseModel):
    """Schema for location-based requests."""
    lat: float
    lng: float
