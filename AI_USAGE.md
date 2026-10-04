# AI usage

## Tools

- **Cursor** (agent mode) with **Grok 4.6** as the coding assistant
- Local Docker for compose/build/test
- No other agents or autocomplete tools were used for this submission

## How the work was split

I set the product and architecture choices before implementation: FastAPI + Vue 3, Postgres, synchronous import, email-then-name identity, `last_sync_succeeded_at` vs attempt metadata, a `VcsProvider` seam without GitLab/Bitbucket clients, and a six-hour cut of scope.

The agent scaffolded the repository layout, Docker images, SQLAlchemy models, API, Vue screens, tests, and first drafts of these Markdown files. I reviewed the schema, the import/partial-failure behaviour, the API shape against the UI, and rewrote anything that was over-scoped or incorrect.

## One thing the agent produced that I rejected

The agent’s first instinct (and an early draft) was a **background import** (FastAPI `BackgroundTasks` or Celery) plus a `contributors` table maintained during sync.

I rejected both:

- A queue and a polling UI would have eaten the timebox and made the required loading state harder to reason about. Ten GitHub pages fit in one request.
- A separate `contributors` table duplicates data that `GROUP BY` already produces, and it forces identity decisions at write time. Aggregating at read time keeps import idempotent and identity rules easy to change.

The import service also initially landed in `app/services/__init__.py`. I made the agent move it to `import_service.py` so the package layout stays conventional.
