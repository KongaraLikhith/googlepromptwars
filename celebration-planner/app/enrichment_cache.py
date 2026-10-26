"""Bounded, short-lived reuse of validated AI ideas within one worker."""

import asyncio
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic

from .schemas import AIEnrichment


class EnrichmentBusy(Exception):
    """The worker has no capacity for another distinct model request."""


@dataclass(frozen=True)
class _Entry:
    expires_at: float
    value: AIEnrichment


class EnrichmentCache:
    """Reuse successes and join identical calls without retaining failed tasks.

    The cache uses opaque, credential-scoped digests supplied by its caller.
    Entries expire after a fixed TTL; FIFO eviction and ordered expiry keep
    lookups constant-time apart from removing expired entries once each.
    Pending work is separately bounded and never queues distinct model calls.
    All operations run on the worker's event loop, with no await between checking
    and publishing a pending task.
    """

    def __init__(
        self,
        max_entries: int = 128,
        ttl_seconds: float = 300,
        max_pending: int = 4,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_entries < 1 or ttl_seconds <= 0 or max_pending < 1:
            raise ValueError("Cache bounds must be positive.")
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.max_pending = max_pending
        self.clock = clock
        self._entries: OrderedDict[str, _Entry] = OrderedDict()
        self._pending: dict[str, asyncio.Task[AIEnrichment]] = {}

    def _expire(self) -> None:
        now = self.clock()
        while self._entries:
            first = next(iter(self._entries.values()))
            if first.expires_at > now:
                break
            self._entries.popitem(last=False)

    async def get_or_create(
        self, key: str, create: Callable[[], Awaitable[AIEnrichment]]
    ) -> AIEnrichment:
        self._expire()
        entry = self._entries.get(key)
        if entry is not None:
            return entry.value.model_copy(deep=True)

        task = self._pending.get(key)
        if task is None:
            if len(self._pending) >= self.max_pending:
                raise EnrichmentBusy

            async def produce() -> AIEnrichment:
                value = await create()
                self._expire()
                if len(self._entries) >= self.max_entries:
                    self._entries.popitem(last=False)
                self._entries[key] = _Entry(
                    self.clock() + self.ttl_seconds, value.model_copy(deep=True)
                )
                return value

            task = asyncio.create_task(produce())
            self._pending[key] = task

            def finished(completed: asyncio.Task[AIEnrichment]) -> None:
                self._pending.pop(key, None)
                # A caller may disconnect before a bounded producer finishes.
                # Retrieve any exception even when no waiter remains.
                if not completed.cancelled():
                    completed.exception()

            task.add_done_callback(finished)

        # Cancelling one waiter must not abort work still needed by another.
        value = await asyncio.shield(task)
        return value.model_copy(deep=True)
