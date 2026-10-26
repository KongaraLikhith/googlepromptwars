"""Gatherly API and same-origin static frontend."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .ai import enrich_plan
from .planner import build_plan
from .schemas import PlanRequest, PlanResponse

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY_BYTES = 8192


class RequestLimitMiddleware:
    """Bound request memory even for chunked clients without Content-Length."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        try:
            size = int(headers.get(b"content-length", b"0"))
        except ValueError:
            await JSONResponse({"detail": "Invalid content length."}, status_code=400)(scope, receive, send)
            return
        if size < 0 or size > MAX_BODY_BYTES:
            await JSONResponse({"detail": "Request is too large."}, status_code=413)(scope, receive, send)
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > MAX_BODY_BYTES:
                await JSONResponse({"detail": "Request is too large."}, status_code=413)(scope, receive, send)
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


app = FastAPI(title="Gatherly — Celebration & Event Planner", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(RequestLimitMiddleware)


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, error: RequestValidationError):
    # Do not echo user notes or non-JSON NaN/Infinity values in validation errors.
    return JSONResponse({"detail": [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]}
        for item in error.errors()
    ]}, status_code=422)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    )
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    return response


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Gatherly"}


@app.post("/api/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    return await enrich_plan(request, build_plan(request))


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# Resolve from this module, so startup works from any working directory.
app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")
