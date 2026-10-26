import asyncio
import json

import pytest

from app.security import RequestLimitMiddleware, SlidingWindowRateLimiter


def test_rate_limit_releases_slots_as_each_request_expires():
    now = 100.0
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, clock=lambda: now)
    assert limiter.retry_after("alice") is None
    now = 104.0
    assert limiter.retry_after("alice") is None
    assert limiter.retry_after("alice") == 6
    assert limiter.retry_after("bob") is None
    now = 110.0
    assert limiter.retry_after("alice") is None
    assert limiter.retry_after("alice") == 4
    now = 120.0
    assert limiter.retry_after("alice") is None


def test_many_clients_cannot_grow_rate_limiter_memory_without_bound():
    now = 0.0
    limiter = SlidingWindowRateLimiter(max_clients=3, window_seconds=10, clock=lambda: now)
    for index in range(100):
        assert limiter.retry_after(f"client-{index}") is None
    assert len(limiter._clients) == 3
    now = 11.0
    assert limiter.retry_after("new-client") is None
    assert len(limiter._clients) == 1


def run_body_request(headers, chunks, *, delay=0):
    received = []
    responses = []

    async def downstream(_scope, receive, send):
        received.append((await receive())["body"])
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def receive():
        if delay:
            await asyncio.sleep(delay)
        return chunks.pop(0)

    async def send(message):
        responses.append(message)

    asyncio.run(
        RequestLimitMiddleware(downstream)(
            {"type": "http", "method": "POST", "headers": headers},
            receive,
            send,
        )
    )
    return received, responses


@pytest.mark.parametrize("lengths", [[b"bad"], [b"-1"], [b"1", b"1"]])
def test_malformed_content_length_is_rejected_before_reading(lengths):
    received, responses = run_body_request([(b"content-length", value) for value in lengths], [])
    assert not received
    assert responses[0]["status"] == 400


def test_bounded_chunked_body_is_replayed_once_without_changing_its_content():
    received, responses = run_body_request(
        [],
        [
            {"type": "http.request", "body": b'{"hello":', "more_body": True},
            {"type": "http.request", "body": b'"world"}', "more_body": False},
        ],
    )
    assert received == [b'{"hello":"world"}']
    assert responses[0]["status"] == 204


def test_declared_oversized_body_is_rejected_before_reading():
    received, responses = run_body_request([(b"content-length", b"8193")], [])
    assert not received
    assert responses[0]["status"] == 413


def test_partial_body_cannot_hold_a_worker_forever(monkeypatch):
    monkeypatch.setattr("app.security.BODY_TIMEOUT_SECONDS", 0.01)
    received, responses = run_body_request(
        [],
        [
            {"type": "http.request", "body": b"partial", "more_body": True},
        ],
        delay=0.05,
    )
    assert not received
    assert responses[0]["status"] == 408
    assert json.loads(responses[1]["body"])["detail"] == "Request body timed out."


def test_disconnected_body_is_not_sent_to_application():
    received, responses = run_body_request([], [{"type": "http.disconnect"}])
    assert not received and not responses
