from fastapi import APIRouter
from services.calendar_service import get_india_election_events

router = APIRouter()

@router.get("/api/election-events")
async def election_events_endpoint():
    try:
        events = get_india_election_events()
        return {"events": events, "success": True}
    except Exception as e:
        return {"events": [], "success": False, "error": str(e)}
