"""Gatherly API and same-origin static frontend."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ai import enrich_plan
from .planner import build_plan
from .schemas import PlanRequest, PlanResponse, SampleResponse
from .security import RequestLimitMiddleware, SecurityHeadersMiddleware, SlidingWindowRateLimiter

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Reuse provider connections within a worker and close them on shutdown."""
    if not os.getenv("GEMINI_API_KEY"):
        yield
        return
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(45.0, connect=4.0),
        limits=httpx.Limits(max_connections=4, max_keepalive_connections=4),
        follow_redirects=False,
    ) as client:
        application.state.ai_client = client
        try:
            yield
        finally:
            application.state.ai_client = None


app = FastAPI(
    title="Gatherly — Celebration & Event Planner",
    version="1.2.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(RequestLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.state.plan_limiter = SlidingWindowRateLimiter()
app.state.ai_client = None


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, error: RequestValidationError) -> JSONResponse:
    # Do not echo user notes or non-JSON NaN/Infinity values in validation errors.
    return JSONResponse(
        {
            "detail": [
                {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
                for item in error.errors()
            ]
        },
        status_code=422,
    )


@app.get("/health")
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "Gatherly"}


@app.get("/api/sample", response_model=SampleResponse)
async def sample_plan() -> SampleResponse:
    """A useful first screen without a paid model call or submitted user data."""
    brief = PlanRequest(
        event_type="birthday",
        event_date=date.today() + timedelta(days=90),
        budget=50000,
        currency="INR",
        guest_count=40,
        style="Relaxed garden gathering",
        priorities=["food", "decor"],
    )
    plan = build_plan(brief)
    plan.source_note = (
        "Sample plan with local estimates and curated ideas. "
        "Customize your brief and create a plan for personalized Gemini ideas when available."
    )
    return SampleResponse(brief=brief, plan=plan)


@app.post("/api/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest, http_request: Request) -> PlanResponse:
    # Validation runs first; invalid requests do not consume the planning quota.
    client = http_request.client.host if http_request.client else "unknown"
    retry_after = app.state.plan_limiter.retry_after(client)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many plans requested. Please wait before creating another plan.",
            headers={"Retry-After": str(retry_after)},
        )
    return await enrich_plan(request, build_plan(request), client=app.state.ai_client)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Resolve from this module, so startup works from any working directory.
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")
