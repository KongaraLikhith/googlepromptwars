"""Reproducible CPU observations; never calls Gemini or requires a credential.

Run from celebration-planner: python -m scripts.benchmark --iterations 2000
Results depend on the machine and are observations, not latency guarantees.
"""

import argparse
import json
import platform
from collections.abc import Callable
from datetime import date, timedelta
from statistics import median
from time import perf_counter_ns

from app.planner import build_plan
from app.schemas import PlanRequest
from app.security import SlidingWindowRateLimiter


def measure(operation: Callable[[], object], iterations: int) -> dict[str, float]:
    durations = []
    for _ in range(iterations):
        started = perf_counter_ns()
        operation()
        durations.append((perf_counter_ns() - started) / 1000)
    durations.sort()
    return {
        "median_microseconds": round(median(durations), 2),
        "p95_microseconds": round(durations[int((iterations - 1) * 0.95)], 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=2000)
    args = parser.parse_args()
    if not 100 <= args.iterations <= 100000:
        parser.error("Choose between 100 and 100000 iterations.")
    brief = PlanRequest(
        event_type="community",
        event_date=date.today() + timedelta(days=90),
        budget="100000000.00",
        guest_count=10000,
        priorities=["food", "venue", "accessibility"],
        preferences="x" * 500,
    )
    limiter = SlidingWindowRateLimiter(limit=args.iterations + 1)
    for index in range(1024):
        limiter.retry_after(f"client-{index}")
    report = {
        "python": platform.python_version(),
        "iterations": args.iterations,
        "network_calls": 0,
        "largest_supported_event_plan": measure(lambda: build_plan(brief), args.iterations),
        "limiter_with_1024_clients": measure(
            lambda: limiter.retry_after("client-0"), args.iterations
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
