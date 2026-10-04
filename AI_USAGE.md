# AI usage

## Tools

- **Cursor** (agent mode) with **Grok 4.7** as the coding assistant
- Local Docker for compose/build/test
- No other agents or autocomplete tools were used for this submission

## How the work was split

I set the product and architecture choices before implementation: FastAPI + Vue 3, Postgres, synchronous import, email-then-name identity, `last_sync_succeeded_at` vs attempt metadata, a `VcsProvider` seam without GitLab/Bitbucket clients, and a six-hour cut of scope.

The agent scaffolded the repository layout, Docker images, SQLAlchemy models, API, Vue screens, tests, and first drafts of these Markdown files. One correction I made after that draft: `GET /api/health` always returned `{"status": "ok"}`. Compose starts the frontend only after that route succeeds, and `wait_for_db()` only runs at boot, so a Postgres outage after startup still looked ready. I changed the handler to run `SELECT 1` and return 503 `{"status": "unavailable"}` when the database does not answer.

## One thing the agent produced that I rejected

The agent’s first instinct (and an early draft) was a **background import** (FastAPI `BackgroundTasks` or Celery) plus a `contributors` table maintained during sync.

I rejected both:

- A queue and a polling UI would have eaten the timebox and made the required loading state harder to reason about. Ten GitHub pages fit in one request.
- A separate `contributors` table duplicates data that `GROUP BY` already produces, and it forces identity decisions at write time. Aggregating at read time keeps import idempotent and identity rules easy to change.
