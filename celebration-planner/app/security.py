"""Small, bounded protections for the public, unauthenticated planner."""

import asyncio
import math
from collections import OrderedDict, deque
from collections.abc import Callable
from time import monotonic

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 8192
BODY_TIMEOUT_SECONDS = 10.0


def _declared_length(scope: Scope) -> int:
    """Reject ambiguous framing without reading a body or echoing its values."""
    lengths = [value for name, value in scope["headers"] if name == b"content-length"]
    if len(lengths) > 1 or (lengths and not lengths[0].isdigit()):
        raise ValueError("Invalid content length")
    return int(lengths[0]) if lengths else 0


class _BodyTooLarge(Exception):
    """A streamed body exceeded the same limit as a declared body."""


async def _read_body(receive: Receive) -> bytes | None:
    """Read once with bounded memory/time; None means the client disconnected."""
    body = bytearray()
    async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return None
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > MAX_BODY_BYTES:
                raise _BodyTooLarge
            body.extend(chunk)
            if not message.get("more_body", False):
                return bytes(body)


class SlidingWindowRateLimiter:
    """Best-effort per-worker limit; never trust a client-supplied proxy header.

    The synchronous check contains no await, so each event loop updates its state
    atomically. Expiry and eviction keep memory bounded even with many clients.
    Serverless instances have independent counters; this is not a global quota.
    """

    def __init__(
        self,
        limit: int = 12,
        window_seconds: float = 600,
        max_clients: int = 1024,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if limit < 1 or window_seconds <= 0 or max_clients < 1:
            raise ValueError("Rate limit settings must be positive.")
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self.clock = clock
        self._clients: OrderedDict[str, deque[float]] = OrderedDict()

    def retry_after(self, client: str) -> int | None:
        """Record an allowed request, or return seconds until a slot is free."""
        now = self.clock()
        cutoff = now - self.window_seconds
        # Ordered by the most recent accepted hit: discard only expired heads.
        # Each client is removed once, avoiding a full scan on every request.
        while self._clients:
            first = next(iter(self._clients.values()))
            if first[-1] > cutoff:
                break
            self._clients.popitem(last=False)
        hits = self._clients.get(client)
        if hits is None:
            if len(self._clients) >= self.max_clients:
                self._clients.popitem(last=False)
            hits = self._clients[client] = deque()
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, math.ceil(hits[0] + self.window_seconds - now))
        hits.append(now)
        self._clients.move_to_end(client)
        return None


class RequestLimitMiddleware:
    """Bound request bytes and total body-read time, including chunked bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return
        try:
            size = _declared_length(scope)
        except ValueError:
            await JSONResponse({"detail": "Invalid content length."}, status_code=400)(
                scope, receive, send
            )
            return
        if size > MAX_BODY_BYTES:
            await JSONResponse({"detail": "Request is too large."}, status_code=413)(
                scope, receive, send
            )
            return
        try:
            body = await _read_body(receive)
        except _BodyTooLarge:
            await JSONResponse({"detail": "Request is too large."}, status_code=413)(
                scope, receive, send
            )
            return
        except TimeoutError:
            await JSONResponse({"detail": "Request body timed out."}, status_code=408)(
                scope, receive, send
            )
            return
        if body is None:
            return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class SecurityHeadersMiddleware:
    """Apply the same browser policy to successful and rejected HTTP requests."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def protected_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                policy = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
                    b"cross-origin-resource-policy": b"same-origin",
                    b"cross-origin-opener-policy": b"same-origin",
                    b"content-security-policy": (
                        b"default-src 'self'; script-src 'self'; style-src 'self'; "
                        b"img-src 'self' data:; font-src 'self'; connect-src 'self'; "
                        b"object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
                    ),
                    b"cache-control": b"no-store"
                    if scope["path"].startswith("/api/")
                    else b"no-cache",
                }
                existing = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() not in policy
                ]
                message = {**message, "headers": existing + list(policy.items())}
            await send(message)

        await self.app(scope, receive, protected_send)
