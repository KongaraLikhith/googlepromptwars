from fastapi import APIRouter
import logging
from schemas import ChatRequest
from services.gemini_service import get_gemini_response

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Handles user queries about elections and returns AI-generated responses using Gemini.
    """
    try:
        response = await get_gemini_response(request.message, request.history)
        return {"response": response, "success": True}
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}")
        return {"response": f"An error occurred: {str(e)}", "success": False}
