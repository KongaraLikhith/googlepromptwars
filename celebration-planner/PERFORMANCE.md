# Performance checks

Gatherly avoids model work until the host chooses to generate a plan. The limits below are part of the implementation and are tested without a paid API key.

| Operation | Behavior |
| --- | --- |
| Fresh page or reset | One local sample GET, zero Gemini calls |
| Budget edit, tab switch, checklist, export, print | No plan-generation request |
| Repeated identical brief in a warm worker | Reuse validated enrichment within five minutes |
| Concurrent identical briefs | One shared provider task |
| Distinct active Gemini calls | At most four per worker; no unbounded queue |
| Successful enrichment storage | At most 128 entries; expired entries pruned on access |
| Model call | 45-second total deadline, 32 KiB streamed response cap |
| Plan with 10,000 guests | Same fixed category/task counts as a small event |

Only AI ideas and tips are cached. Deterministic budgets and dates are rebuilt from the validated brief. Model, credential, or context changes prevent unintended reuse. Failures are not cached, and there are no automatic provider retries. Limits apply per worker; they do not replace provider quotas or a shared production rate limiter.

## Reproduce locally

Install `requirements-dev.lock`, then run:

```bash
python -m pytest -q
python -m scripts.benchmark --iterations 2000
npm test
```

Start a fresh server without `GEMINI_API_KEY` and run the browser suite in another terminal:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8087
# Another terminal, after npm ci and npx playwright install chromium:
npm run test:browser
```

The browser suite counts requests and asserts zero plan POSTs during sample startup, reset, and non-generation interactions. It records initial workspace-ready time and encoded resource bytes without a fragile time threshold. Cache tests prove provider-call counts, expiry, capacity, independent returned values, and cancellation cleanup. No real model responses are mocked in the production verification; automated failure cases are explicitly mocked.

## Development-container observations

These are measurements from one development container, not production service-level guarantees. Hardware, cold starts, network, provider availability, and worker reuse affect results.

- Browser sample became usable in **323 ms**, with approximately **70 KB** of encoded page resources and **zero AI calls**. The four automated WCAG A/AA scans reported no violations.
- The offline benchmark on Python 3.12.14, 2,000 iterations, observed **27.65 µs median** and **54.0 µs p95** for the largest supported event plan.
- At 1,024 tracked clients, ordered rate-limiter cleanup observed **0.40 µs median** and **0.45 µs p95** per accepted hit in the same benchmark.
- Exact planner output matched the preceding revision across **576** combinations of event type, budget, lead time, guest threshold, style, preferences, and priorities.

The previous first screen generated AI ideas automatically and could wait for the provider. The current sample never waits for a model. Explicit AI generation still depends on Gemini, and temporary provider failures produce a clearly labelled complete local plan.
