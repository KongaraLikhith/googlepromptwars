import asyncio

import pytest

from app.enrichment_cache import EnrichmentBusy, EnrichmentCache
from app.schemas import AIEnrichment


def enrichment(title="A shared activity"):
    return AIEnrichment(
        ideas=[{"title": title, "description": "Offer a seated option."}] * 3,
        tips=["Confirm labels.", "Offer choices.", "Use reusable supplies."],
    )


def test_success_reuse_expires_without_extending_ttl_and_returns_independent_values():
    now = 0.0
    cache = EnrichmentCache(ttl_seconds=5, clock=lambda: now)
    calls = 0

    async def create():
        nonlocal calls
        calls += 1
        return enrichment()

    async def exercise():
        nonlocal now
        first = await cache.get_or_create("opaque-context", create)
        first.ideas[0].title = "User edited this result"
        now = 4
        second = await cache.get_or_create("opaque-context", create)
        assert second.ideas[0].title == "A shared activity"
        assert calls == 1
        now = 5
        await cache.get_or_create("opaque-context", create)
        assert calls == 2

    asyncio.run(exercise())


def test_cache_capacity_evicts_oldest_success():
    cache = EnrichmentCache(max_entries=2)
    calls = 0

    async def create():
        nonlocal calls
        calls += 1
        return enrichment()

    async def exercise():
        for key in ["first", "second", "third", "second", "first"]:
            await cache.get_or_create(key, create)
        assert calls == 4  # Second is reusable; first was evicted.

    asyncio.run(exercise())


def test_identical_concurrent_requests_share_one_producer_even_at_capacity():
    cache = EnrichmentCache(max_pending=1)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def create():
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return enrichment()

    async def exercise():
        owner = asyncio.create_task(cache.get_or_create("same", create))
        await started.wait()
        follower = asyncio.create_task(cache.get_or_create("same", create))
        with pytest.raises(EnrichmentBusy):
            await cache.get_or_create("different", create)
        release.set()
        first, second = await asyncio.gather(owner, follower)
        assert calls == 1
        assert first == second and first is not second

    asyncio.run(exercise())


def test_cancelling_one_waiter_does_not_cancel_the_shared_request():
    cache = EnrichmentCache()
    started = asyncio.Event()
    joined = asyncio.Event()
    release = asyncio.Event()

    async def create():
        started.set()
        await release.wait()
        return enrichment()

    async def follow():
        joined.set()
        return await cache.get_or_create("same", create)

    async def exercise():
        owner = asyncio.create_task(cache.get_or_create("same", create))
        await started.wait()
        follower = asyncio.create_task(follow())
        await joined.wait()
        follower.cancel()
        with pytest.raises(asyncio.CancelledError):
            await follower
        release.set()
        assert (await owner).ideas[0].title == "A shared activity"

    asyncio.run(exercise())


def test_failed_and_cancelled_producers_are_not_cached_or_left_using_capacity():
    cache = EnrichmentCache(max_pending=1)
    calls = 0

    async def fail():
        nonlocal calls
        calls += 1
        raise ValueError("Invalid model result")

    async def cancelled():
        raise asyncio.CancelledError

    async def succeed():
        return enrichment()

    async def exercise():
        for _ in range(2):
            with pytest.raises(ValueError):
                await cache.get_or_create("same", fail)
        with pytest.raises(asyncio.CancelledError):
            await cache.get_or_create("same", cancelled)
        result = await cache.get_or_create("same", succeed)
        assert result.ideas[0].title == "A shared activity" and calls == 2

    asyncio.run(exercise())


def test_orphaned_failure_is_retrieved_and_capacity_recovers():
    cache = EnrichmentCache(max_pending=1)
    started = asyncio.Event()
    release = asyncio.Event()
    finished = asyncio.Event()

    async def fail():
        started.set()
        await release.wait()
        try:
            raise ValueError("A caller disconnected before this failure")
        finally:
            finished.set()

    async def succeed():
        return enrichment()

    async def exercise():
        loop = asyncio.get_running_loop()
        unhandled = []
        loop.set_exception_handler(lambda _loop, context: unhandled.append(context))
        owner = asyncio.create_task(cache.get_or_create("same", fail))
        await started.wait()
        owner.cancel()
        with pytest.raises(asyncio.CancelledError):
            await owner
        release.set()
        await finished.wait()
        # Run the task completion callback before requesting new capacity.
        await asyncio.sleep(0)
        assert (await cache.get_or_create("different", succeed)).ideas
        assert unhandled == []

    asyncio.run(exercise())
