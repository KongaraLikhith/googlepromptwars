# Challenge 5 submission notes

## Project

**Gatherly — Celebration & Event Planner**

Repository link: `https://github.com/KongaraLikhith/googlepromptwars`

Deployed project: `https://gatherly-celebration-planner-c5.vercel.app`

Challenge 5 source directory: [`celebration-planner`](./).

Before submitting, push this project to the public repository and verify the link works in a signed-out browser. Keep the source repository below 10 MB. Environment virtual environments and package caches live outside the checkout and must not be committed.

Keep one published branch (`master`) in the repository. This existing repository contains earlier challenges in separate directories; Challenge 5 code and documentation are in `celebration-planner/`.

## Suggested deployed-version description

Optimized Gatherly's first screen and reset to load a local sample without spending AI tokens. Added bounded five-minute reuse of validated Gemini ideas, shared work for identical concurrent requests, and pooled provider connections. Refactored planning into small typed functions with immutable event templates, and separated frontend rendering, request handling, and state. Reused browser locale formatters and improved rate-limit expiry. Retained exact-cent budgets, adaptive timelines, vendor checklists, accessible keyboard flows, local save/export/print, and honest AI fallback. Expanded automated tests for cache expiry, concurrency, cancellation, isolation, and zero-AI startup/reset; documented reproducible performance checks.

## Suggested GenAI description

Google Gemini personalizes celebration ideas and practical planning tips from the user's event type, style, priorities, guest count, and bounded preferences. It is called from the FastAPI backend through the Gemini REST API; the key stays on the server. Budget arithmetic, timeline dates, and checklist items come from an inspectable deterministic engine. The interface labels Gemini and local results, and the app remains usable when a key is absent or the model is unavailable.

## Demo recording outline

1. Introduce the problem: managing event costs, deadlines, and vendors across separate notes.
2. Create a birthday plan, then switch to wedding or community and change priorities.
3. Explain category allocations and contingency; edit a category to demonstrate the over-budget warning.
4. Open the timeline and show how dates adapt to the event date.
5. Complete checklist items, refresh, and show that local progress persists.
6. Show personalized ideas and clearly identify whether the recording uses Gemini or local mode.
7. Export the plan or print it, then show the test result and explain that secrets stay on the server.

## Required fields to complete before submission

- Select **Challenge 5 — Celebration & Event Planner**.
- Enter the public GitHub repository link after pushing and checking public access.
- Enter the actual public deployment URL after deploying and testing it.
- Record a demo and supply an unlisted YouTube link or a publicly accessible Drive link.
- Add the deployed-version and GenAI descriptions above, editing them to match the deployed build.
- Publish your own LinkedIn post and enter its actual HTTPS URL.

The platform permits only three submissions. Validate all links and ensure the deployed app matches the repository before using an attempt.

Demo video: `https://youtu.be/fgtzl3VfrTo`

LinkedIn post: `https://lnkd.in/p/e5XktsDg`
