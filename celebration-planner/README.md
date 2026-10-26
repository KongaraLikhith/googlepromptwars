# Gatherly — Celebration & Event Planner

Challenge 5: a GenAI-powered assistant for weddings, birthdays, and community events. Turn a few practical details into a budget, preparation timeline, vendor checklist, and personal celebration ideas.

**Live app:** [gatherly-celebration-planner-c5.vercel.app](https://gatherly-celebration-planner-c5.vercel.app)

Gatherly works without an account or API key. Its local mode is clearly labelled. Configure Gemini to personalize ideas while the inspectable planning engine continues to control the numbers and dates.

The first screen loads a local sample without calling Gemini. Customize the brief and choose **Create my celebration plan** to request AI ideas. Resetting also loads a local sample; opening or exploring the page does not spend AI tokens.

## Run locally

Requires Python 3.12 or newer. From this directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

Visit the local server on port 8080. The frontend and API share one server; there is no frontend build step or database.

For the prepared Codex cloud environment, use its external virtual environment instead:

```bash
/workspace/.cloud-environment/googlepromptwars/venvs/celebration-planner/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8085
```

## What you can do

- Plan a wedding, birthday, or community gathering with a date, location, guest count, currency, budget, style, and up to three priorities.
- Get a complete budget with a contingency reserve. Edit individual allocations, see overspending, and compare cost per guest.
- Follow a preparation timeline that adapts to the event date, including catch-up tasks for short lead times.
- Track vendors and practical tasks, with completion progress saved in the browser.
- Explore personalized ideas and practical planning tips. Gemini mode is identified separately from the local suggestions.
- Save and restore your plan locally, export it as JSON, or print a planning brief using your browser.

The interface supports keyboard navigation, visible focus indicators, labelled inputs, responsive layouts, accessible status messages, and reduced-motion preferences. It uses no external fonts or media downloads.

## Optional Gemini integration

Set `GEMINI_API_KEY` in the server process or your deployment's secure environment settings. `GEMINI_MODEL` defaults to `gemini-3.5-flash-lite` and can be changed to a model available to your Google project. `.env.example` documents the names; the application does not load a `.env` file automatically.

The backend calls the Gemini REST API over HTTPS through `httpx`. Only bounded event preferences are sent to Gemini. Do not enter guest names, contact details, payment details, or other private information in the preference field. A failed or unavailable model falls back to useful local suggestions and reports the source honestly.

Gemini writes ideas and tips. It does not set budget totals, choose dates, contact vendors, make purchases, or make bookings. All allocations are planning estimates rather than real quotes. Confirm costs, accessibility needs, permissions, and availability with the venue and vendors.

## Architecture

```text
Browser: semantic HTML + CSS + JavaScript
  ├─ editable planning workspace and browser-local checklist
  ├─ GET /api/sample → deterministic first screen, no AI call
  └─ POST /api/plan
       ├─ FastAPI validation
       ├─ deterministic budget / timeline / vendor engine
       └─ bounded enrichment cache → optional pooled Gemini request
```

The intended user is a host planning a wedding or birthday, or a volunteer organizing a community gathering. They need a usable first plan before they have vendor quotes, rather than a chatbot transcript they must turn into a checklist themselves.

### Approach and context decisions

| User context | Planning decision |
| --- | --- |
| Wedding, birthday, or community event | Different category weights, ideas, and ceremony, cake, or permits tasks |
| Up to three priorities | Increase the selected categories' weights while preserving the total |
| Any supported budget | Reserve 10% contingency; distribute all cents with largest-remainder allocation |
| Short lead time | Move overdue preparation tasks to today and explain the catch-up work |
| More than 200 guests | Add capacity, staffing, and emergency-planning guidance |
| Style, location, and preferences | Include context in the brief and optional Gemini ideas |
| Missing, busy, invalid, or unavailable AI | Keep the complete deterministic plan and label local suggestions |

Currency is a unit selected by the user, not an exchange-rate conversion. Budgets are estimates; the engine does not infer vendor prices from a city name. Dates use the server's calendar day, with a planning window from today through 730 days ahead. The default category shares and 10% reserve are explicit planning assumptions, not a guarantee that an event is affordable.

### Code map

- `app/schemas.py`: bounded input and AI-output contracts.
- `app/planner.py`: small typed functions for budgets, timelines, vendors, ideas, and context decisions.
- `app/planning_data.py`: immutable event templates and planning assumptions.
- `app/ai.py`: Gemini request validation, deadlines, safe fallback, and credential-scoped context keys.
- `app/enrichment_cache.py`: bounded success reuse and identical-request coalescing.
- `app/security.py`: typed ASGI body limits, response headers, and bounded request throttling.
- `app/main.py`: API routes and static-file serving.
- `app/static/app.js`: controller and interaction state.
- `app/static/plan-view.js`, `plan-api.js`, `plan-utils.js`, `plan-storage.js`: rendering, requests, pure helpers/locale formatters, and validated browser storage.
- `tests/`: planner/API/AI/security tests, frontend unit tests, and browser/accessibility checks.

The server has no database or durable event-plan storage. A sample remains in memory until the user edits it or explicitly generates a plan; those edits and generated plans save automatically in the current browser, with visible status. Clearing or exporting a plan is under the user's control. Successful AI ideas can be reused briefly in worker memory as described below. Gemini receives event context only on explicit plan generation when server-side AI is configured; its provider policies still apply. Logs record safe failure metadata, excluding keys, prompts, preferences, and model output.

### Efficiency and resource bounds

- Startup and reset use a deterministic sample endpoint: zero Gemini requests.
- Successful ideas and tips have a five-minute reuse window in a cache limited to 128 entries per worker. Keys are HMAC digests scoped to the model, server credential, and normalized event context; raw briefs and API keys are not stored as cache keys. Expired entries are removed on the next cache access; worker shutdown also releases memory. The cache stores validated AI enrichment only, never complete plans, and returns independent copies.
- Concurrent identical briefs share one provider task. Up to four distinct calls run per worker; additional distinct calls use the labelled local fallback immediately. Failures are not cached or automatically retried. Cancelling one waiter does not cancel work shared by another.
- The application lifespan reuses an HTTP connection pool and closes it on shutdown. Request deadlines and response-size limits remain in force.
- Immutable templates are created once. Planning cost does not grow with guest count. Rate-limiter expiry removes ordered expired entries once instead of scanning every tracked client per request.
- Browser rendering reuses a bounded set of locale formatters and fixed DOM references. There are no frontend runtime packages, external fonts, or media requests.

Cache and throttle state are local to a worker and are lost on cold starts; multiple serverless instances do not share them. See [PERFORMANCE.md](PERFORMANCE.md) for reproducible checks and measured observations.

### Security boundaries

The API rejects unknown fields and oversized bodies (8 KiB), limits body reading to ten seconds, validates dates, amounts and text, and renders user/model content as text. Same-origin CSP, frame protection, MIME protection, and restricted browser permissions apply to normal and handled error responses. Gemini responses are capped at 32 KiB while streaming, schema-validated, and subject to a 45-second total deadline and four concurrent calls per worker. No automatic retries multiply model charges.

Valid plan requests are limited to 12 per client address per ten minutes, returning HTTP 429 with `Retry-After`. The bounded in-memory limiter uses the ASGI client address and ignores forwarded headers supplied by a caller. It is a best-effort per-worker limit: cold starts and multiple serverless instances do not share counters, and hosts behind a proxy may share an address. Configure provider quotas and an edge/shared rate limiter for broader public traffic. This app has no authentication, booking, payment, or vendor-contact capability.

## Tests

For development, install the separate hashed development lockfile in the virtual environment. Python runtime deployments exclude the testing and lint tools.

```bash
python -m pip install --require-hashes -r requirements-dev.lock
ruff check app tests scripts
ruff format --check app tests scripts
python -m pytest -q
```

Frontend unit tests require Node.js 22 or newer and use its built-in test runner:

```bash
npm test
```

For the browser suite, install the pinned development-only packages and Chromium:

```bash
npm ci
npx playwright install chromium
```

Start a fresh local server **without** `GEMINI_API_KEY` on port 8087, then run the suite from another terminal:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8087
# In another terminal:
npm run test:browser
```

`BASE_URL` overrides the server URL; `CHROMIUM_PATH` selects an existing Chromium executable. The suite checks all event types, exact-cent totals, edits/export, checklist persistence, keyboard tabs, failure recovery, print, six viewport widths, and axe WCAG A/AA scans. Automated accessibility checks cover common issues; they do not replace assistive-technology user testing.

Python tests cover arithmetic, all supported priority combinations, template isolation, scheduling, validation, body limits, throttling, security headers, connection-pool lifecycle, and mocked Gemini success, timeout, malformed output, size limits, and fallback. Cache tests check expiry, capacity, concurrent reuse, cancellation, mutation isolation, and credential/context separation. Frontend tests cover request deadlines, sample validation, money/date helpers, formatter reuse, and malformed or unavailable browser storage. Ruff also limits function complexity to ten. These automated suites need no paid AI key; successful Gemini integration must also be checked against the live deployment. `requirements.lock` pins runtime artifacts with hashes; `requirements-dev.lock` adds test/lint tools, and `package-lock.json` pins browser-test tools. No Node packages are shipped to the browser.

## Vercel deployment

Import `KongaraLikhith/googlepromptwars` into a **new** Vercel project and set its **Root Directory** to `celebration-planner`. Keep the earlier challenge projects and their deployment settings unchanged.

Vercel detects the FastAPI application at `app/main.py`. The included `vercel.json` selects the FastAPI framework and installs the hashed dependency lockfile, while `.python-version` pins Python 3.12. No custom build command, output directory, or URL rewrite is needed. The frontend, static assets, health endpoint, and `/api/plan` are served by the same application.

In the new project's **Settings → Environment Variables**, add:

| Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | A new Gemini API key entered securely in Vercel |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite`, or another model available to your Google project |

Set the variables for the deployment environments you will use, then deploy or redeploy. Never paste real keys into source files, `vercel.json`, command-line arguments, commits, or logs. `.vercelignore` excludes local secret files, virtual environments, caches, and tests from the upload.

Verify the deployed page and its health endpoint, create a plan for each of the three event types, and confirm that live AI results show **Gemini ideas**. A working local fallback alone does not verify the Gemini integration. Check budget edits, checklist persistence, export, and mobile layout before recording the demo. Vercel and Google quotas still apply; this project does not require Cloud Run.

## Optional container deployment

```bash
docker build -t gatherly .
docker run --rm -p 8080:8080 gatherly
```

Supply optional keys through your host's secure secret settings. The container runs as a non-root user and listens on port 8080. Deploy it to any container host, including Google Cloud Run. For example, after configuring your own Google Cloud project and authentication:

```bash
gcloud run deploy gatherly --source . --region asia-south1 --allow-unauthenticated --port 8080
```

Container deployment requires your cloud account and may incur provider charges. Vercel is the intended hosting route for this submission. See [SUBMISSION.md](SUBMISSION.md) for the Challenge 5 submission checklist and suggested descriptions; enter actual deployment, video, and social links after publishing them.

## Scope and limitations

Currency selection changes the unit and display; it does not convert prices or provide market quotes. Local planning uses documented category shares rather than location-specific vendor pricing. The assistant does not manage invitations, accounts, payments, or live vendor availability. There is no durable server-side plan storage; the bounded AI enrichment cache temporarily holds generated ideas in worker memory. Browser storage belongs to the current browser and device.
