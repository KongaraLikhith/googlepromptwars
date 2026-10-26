# Gatherly — Celebration & Event Planner

Challenge 5: a GenAI-powered assistant for weddings, birthdays, and community events. Turn a few practical details into a budget, preparation timeline, vendor checklist, and personal celebration ideas.

Gatherly works without an account or API key. Its local mode is clearly labelled. Configure Gemini to personalize ideas while the inspectable planning engine continues to control the numbers and dates.

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

Set `GEMINI_API_KEY` in the server process or your deployment's secure environment settings. `GEMINI_MODEL` defaults to `gemini-2.5-flash` and can be changed to a model available to your Google project. `.env.example` documents the names; the application does not load a `.env` file automatically.

The backend calls the Gemini REST API over HTTPS through `httpx`. Only bounded event preferences are sent to Gemini. Do not enter guest names, contact details, payment details, or other private information in the preference field. A failed or unavailable model falls back to useful local suggestions and reports the source honestly.

Gemini writes ideas and tips. It does not set budget totals, choose dates, contact vendors, make purchases, or make bookings. All allocations are planning estimates rather than real quotes. Confirm costs, accessibility needs, permissions, and availability with the venue and vendors.

## Architecture

```text
Browser: semantic HTML + CSS + JavaScript
  ├─ editable planning workspace and browser-local checklist
  └─ POST /api/plan
       ├─ FastAPI validation
       ├─ deterministic budget / timeline / vendor engine
       └─ optional Gemini REST request for ideas and tips
```

The server is stateless and does not store plans. Browser storage can be cleared from the interface. JSON export is explicit. API validation bounds budgets, guest counts, dates, and text lengths. Security headers and a request-size limit protect the application boundary; model output is rendered as text.

## Tests

From this directory with the virtual environment activated:

```bash
python -m pytest -q
```

The tests cover budget arithmetic, event-specific plans and priorities, scheduling, API validation, security headers, and mocked Gemini success and fallback paths. They do not require a paid API key or make live Google requests. Dependencies are pinned transitively with artifact hashes in `requirements.lock`; `requirements.txt` lists the direct dependencies.

## Vercel deployment

Import `KongaraLikhith/googlepromptwars` into a **new** Vercel project and set its **Root Directory** to `celebration-planner`. Keep the earlier challenge projects and their deployment settings unchanged.

Vercel detects the FastAPI application at `app/main.py`. The included `vercel.json` selects the FastAPI framework and installs the hashed dependency lockfile, while `.python-version` pins Python 3.12. No custom build command, output directory, or URL rewrite is needed. The frontend, static assets, health endpoint, and `/api/plan` are served by the same application.

In the new project's **Settings → Environment Variables**, add:

| Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | A new Gemini API key entered securely in Vercel |
| `GEMINI_MODEL` | `gemini-2.5-flash`, or another model available to your Google project |

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

Currency selection changes the unit and display; it does not convert prices or provide market quotes. Local planning uses documented category shares rather than location-specific vendor pricing. The assistant does not manage invitations, accounts, payments, or live vendor availability. No event information is persisted on the server. Browser storage belongs to the current browser and device.
