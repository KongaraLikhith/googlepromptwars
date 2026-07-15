from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from .calculator import UserInputs, calculate_footprint
from .assistant import get_insights, get_chat_response

load_dotenv()

app = FastAPI(title="Carbon Footprint Platform")

# Efficiency: GZip Compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security: CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security: Custom Security Headers
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Middleware to inject strict security headers into every response.
    """
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Efficiency: Cache-Control for static files
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=31536000"

    return response


class CalculationResponse(BaseModel):
    """
    Pydantic model representing the API response for the calculate endpoint.
    """

    footprint: dict
    insights: str


@app.post("/api/calculate", response_model=CalculationResponse)
async def calculate_and_get_insights(inputs: UserInputs):
    """
    Endpoint to calculate the carbon footprint and asynchronously fetch dynamic AI insights.

    Args:
        inputs (UserInputs): The payload containing user lifestyle data.

    Returns:
        dict: A dictionary containing footprint metrics and markdown insights.
    """
    footprint = calculate_footprint(inputs)
    insights = await get_insights(footprint)

    return {"footprint": footprint.model_dump(), "insights": insights}


class ChatMessage(BaseModel):
    """
    Pydantic model representing a single chat message.
    """

    role: str
    content: str


class ChatRequest(BaseModel):
    """
    Pydantic model representing the incoming chat request payload.
    """

    message: str
    history: list[ChatMessage]


class ChatResponse(BaseModel):
    """
    Pydantic model representing the outgoing chat response payload.
    """

    response: str


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    """
    Endpoint to handle asynchronous conversational interactions with the Gemini AI.

    Args:
        request (ChatRequest): The incoming user message and conversation history.

    Returns:
        dict: A dictionary containing the AI's response string.
    """
    history_dicts = [
        {"role": msg.role, "content": msg.content} for msg in request.history
    ]
    reply = await get_chat_response(request.message, history_dicts)
    return {"response": reply}


# Ensure the static directory exists before mounting
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def read_index():
    """
    Serves the main HTML interface.
    """
    return FileResponse("app/static/index.html")
