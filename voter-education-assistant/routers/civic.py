from fastapi import APIRouter
import logging
from services.civic_service import get_elections, get_voter_info, get_representatives

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/elections")
async def elections_endpoint(address: str):
    """
    Fetches active elections for a given address.
    """
    try:
        result = await get_elections(address)
        fallback = result.get("fallback", False)
        return {
            "elections": result.get("elections", []),
            "fallback": fallback,
            "success": not fallback,
            "message": result.get("message")
        }
    except Exception as e:
        logger.error(f"Error in elections_endpoint: {e}")
        return {"elections": [], "fallback": True, "success": False, "error": str(e)}

@router.get("/api/voter-info")
async def voter_info_endpoint(address: str, election_id: str = "2000"):
    """
    Fetches specific voter info (like polling locations) for a given address.
    """
    try:
        result = await get_voter_info(address, election_id)
        fallback = result.get("fallback", False)
        return {
            "polling_locations": result.get("pollingLocations", []),
            "early_vote_sites": result.get("earlyVoteSites", []),
            "officials": result.get("state", []),
            "fallback": fallback,
            "success": not fallback,
            "message": result.get("message")
        }
    except Exception as e:
        logger.error(f"Error in voter_info_endpoint: {e}")
        return {"polling_locations": [], "officials": [], "fallback": True, "success": False, "error": str(e)}

@router.get("/api/representatives")
async def representatives_endpoint(address: str):
    """
    Fetches elected representatives for a given address.
    """
    try:
        result = await get_representatives(address)
        fallback = result.get("fallback", False)
        return {
            "offices": result.get("offices", []),
            "officials": result.get("officials", []),
            "fallback": fallback,
            "success": not fallback,
            "message": result.get("message")
        }
    except Exception as e:
        logger.error(f"Error in representatives_endpoint: {e}")
        return {"offices": [], "officials": [], "fallback": True, "success": False, "error": str(e)}
