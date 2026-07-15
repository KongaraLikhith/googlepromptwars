# StadiumPulse — Challenge 4: Smart Stadiums & Tournament Operations

StadiumPulse is a GenAI-enabled matchday copilot for the FIFA World Cup 2026 challenge. It transforms venue signals into concise, multilingual and accessibility-aware guidance for fans, while showing venue teams an explainable operational brief.

## Chosen vertical

**Smart Stadiums & Tournament Operations** — fan navigation, crowd management, accessibility, multilingual assistance, sustainability, and operational decision support.

## What it demonstrates

- **Contextual AI concierge:** a fan asks a natural-language question. Gemini receives only a short question plus coarse, temporary preferences and simulated venue signals, then returns a concise next action in the chosen language.
- **Crowd-aware decisions:** when the north plaza queue is projected to rise, guidance recommends the calmer Gate C route and the operations panel proposes a volunteer reassignment.
- **Accessible experience:** step-free routing is a first-class preference; the UI is keyboard operable, responsive, high-contrast, and uses accessible labels/status messages.
- **Human control and safe boundaries:** operational signals are explicitly marked simulated, staff retain final authority, and the AI prompt disallows emergency, medical, security, and invented "live" advice.
- **Sustainability visibility:** the dashboard exposes waste-diversion progress so teams can act on venue sustainability goals.

## Architecture

```text
Browser (accessible HTML/CSS/JS)
  ├─ renders simulated, transparent venue signals
  └─ POST /api/concierge (question + coarse preferences only)
       └─ Vercel Python function → Gemini Flash
            └─ concise multilingual guidance
```

When `GEMINI_API_KEY` is absent or Gemini is unavailable, the app uses an explicitly labelled local simulation fallback. This makes the prototype usable for reviewers without exposing any secret or presenting fabricated data as live.

## Run locally

The static interface can be opened through any local web server. To use the API locally, install the Vercel CLI and run from this folder:

```bash
npm install -g vercel
vercel dev
```

Copy `.env.example` to `.env` and add a newly generated Gemini API key. Do not commit `.env`. The current default model is `gemini-3.5-flash`; it can be overridden with `GEMINI_MODEL` if your Google project has access to a different supported Gemini model.

## Deploy to Vercel

1. Import the GitHub repository in Vercel.
2. Set **Root Directory** to `stadiumpulse`.
3. Add `GEMINI_API_KEY` in Project Settings → Environment Variables.
4. Deploy. Vercel detects the `api/concierge.py` serverless function automatically.

## Tests

```bash
python -m pytest stadiumpulse/tests
```

## Assumptions and limitations

- Signals, match information, queues, transit, and waste figures are simulated demonstration data; a production integration would consume approved venue, transit, and IoT feeds.
- The app does not collect accounts, ticket identifiers, precise location, or persistent chat history.
- Venue operations, emergency instructions, and public safety messages always require authenticated official systems and trained human approval in production.

## Repository size and submission checklist

The project uses no bundled media or build artifacts. Before submitting, keep the repository public, preserve a single branch, and provide the deployed Vercel URL, repository URL, and required narrative/post through the PromptWars dashboard.
