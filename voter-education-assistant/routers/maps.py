from fastapi import APIRouter
import logging
from schemas import LocationRequest
from services.maps_service import find_polling_stations, geocode_address

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/polling-locations")
async def polling_locations_endpoint(request: LocationRequest):
    """
    Fetches nearby polling locations based on latitude and longitude.
    """
    try:
        locations = await find_polling_stations(request.lat, request.lng)
        return {"locations": locations, "success": True}
    except Exception as e:
        logger.error(f"Error in polling_locations_endpoint: {e}")
        return {"locations": [], "success": False, "error": str(e)}

@router.get("/api/geocode")
async def geocode_endpoint(address: str):
    """
    Converts a human-readable address into geographic coordinates.
    """
    try:
        result = await geocode_address(address)
        if "error" in result:
            return {"result": result, "success": False}
        return {"result": result, "success": True}
    except Exception as e:
        logger.error(f"Error in geocode_endpoint: {e}")
        return {"result": {"error": str(e)}, "success": False}
