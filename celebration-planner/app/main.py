"""Gatherly API and same-origin static frontend."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ai import enrich_plan
from .planner import build_plan
from .schemas import PlanRequest, PlanResponse
from .security import RequestLimitMiddleware, SecurityHeadersMiddleware, SlidingWindowRateLimiter

STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(
    title="Gatherly — Celebration & Event Planner", version="1.1.0", docs_url=None, redoc_url=None
)
app.add_middleware(RequestLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.state.plan_limiter = SlidingWindowRateLimiter()


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
    return await enrich_plan(request, build_plan(request))


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Resolve from this module, so startup works from any working directory.
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")
