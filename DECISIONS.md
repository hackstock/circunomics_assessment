# Decisions

## Import runs in the HTTP request

A 1000-commit import is about 10 GitHub pages: the <a href="https://docs.github.com/en/rest/commits/commits#list-commits" target="_blank" rel="noopener noreferrer">List commits</a> endpoint caps `per_page` at 100. That is slow enough to need a loading state, and fast enough that a job queue would be out of proportion for a six-hour slice.

The UI disables submit/re-sync, shows an explicit “Importing…” message, and waits for the response. nginx <a href="https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_read_timeout" target="_blank" rel="noopener noreferrer"><code>proxy_read_timeout</code></a> is 180 seconds so the proxy does not cut the request off.

If this were production traffic, the next step would be a background job plus a sync status the UI can poll. That is listed under “not built”.

## Stay synchronous; do not use asyncio

The slow path is GitHub pagination (~10 `GET`s for 1000 commits). Each page depends on <a href="https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api#using-link-headers" target="_blank" rel="noopener noreferrer"><code>Link: rel="next"</code></a>, so those calls cannot run in parallel. Async would not make a single import much faster.

<a href="https://fastapi.tiangolo.com/async/#path-operation-functions" target="_blank" rel="noopener noreferrer">FastAPI</a> already runs plain `def` routes in a thread pool, so an import does not freeze list/contributor requests. Switching to `async def` while keeping sync `httpx` and SQLAlchemy would block the event loop and be worse. A full async stack (`AsyncClient`, `AsyncSession`, async ports) is a rewrite without a better product for one user and one import at a time.

If import must not occupy an HTTP request, the next step is a background job plus a status the UI can poll, not asyncio-in-request.

## Rate limits keep already-written commits

Unauthenticated GitHub REST traffic is limited to **60 requests per hour**; a <a href="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens" target="_blank" rel="noopener noreferrer">personal access token</a> raises the primary limit to **5,000 requests per hour** (<a href="https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api" target="_blank" rel="noopener noreferrer">Rate limits for the REST API</a>). Ten pages per 1000-commit import will exhaust the unauthenticated quota quickly. GitHub also returns **403** for <a href="https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api#about-secondary-rate-limits" target="_blank" rel="noopener noreferrer">secondary rate limits</a> and **429** when the primary quota is exceeded.

Each GitHub page is upserted and committed before the next page is fetched. If GitHub returns 403/429 (or another provider error) halfway:

- commits already stored stay stored
- `last_sync_status` becomes `partial` (or `failed` if nothing was written)
- `last_sync_succeeded_at` is **not** updated
- `last_sync_error` holds a short explanation, including rate-limit headers when present

The API still returns HTTP 200 with `message` set so the repository remains visible and the UI can show the error. A GitHub 429 is not turned into HTTP 429: by the time rate-limiting happens I may already have a repo row and commits. A missing GitHub repository is different: HTTP 404, and if I never stored commits I delete the row I just created. An empty Git repository is another GitHub-specific case: List commits returns <a href="https://docs.github.com/en/rest/commits/commits#list-commits" target="_blank" rel="noopener noreferrer">409 Conflict</a>, which I treat as “no commits”, not a failed provider.

Re-imports use PostgreSQL <a href="https://www.postgresql.org/docs/current/sql-insert.html#SQL-ON-CONFLICT" target="_blank" rel="noopener noreferrer"><code>ON CONFLICT DO NOTHING</code></a> on `(repository_id, sha)` so two overlapping syncs cannot insert the same commit twice.

I do not sleep-and-retry. Retrying against a depleted quota would make a long request longer without a clear win in this timebox.

## Contributor identity is email, then name

GitHub’s commit payload exposes the **git** author (`commit.author` name/email), which need not match a GitHub user (<a href="https://docs.github.com/en/rest/commits/commits#list-commits" target="_blank" rel="noopener noreferrer">List commits</a>). Two email addresses are **two contributors**, even if a human would call them the same person.

If `author_email` is missing or empty, identity falls back to a lowercased `author_name`. That is enough to group the common case and avoids inventing an identity graph.

Merging identities (same `author.login`, similar names, plus a manual alias UI) is future work.

## “Last synced” means last *successful* sync

The repository list shows `last_sync_succeeded_at` (“Last successful sync”) and a separate status (`success` / `partial` / `failed`). A failed or partial attempt updates `last_sync_attempted_at` and `last_sync_error` but does not pretend the catalogue is fully current.

## Re-adding a repository is the same as re-syncing

`POST /api/repositories` with an `owner/repo` that already exists for the `github` provider reuses the row and runs the same idempotent import. Idempotency is the unique `(repository_id, sha)` constraint with `ON CONFLICT DO NOTHING`.

## Providers are swappable; only GitHub is implemented

Commits are stored in a provider-neutral shape (`sha`, author, date, `html_url`). `VcsProvider.iter_recent_commits` is the seam. `Repository.provider` is part of the uniqueness key so the same `owner/name` can exist on GitLab later without colliding. GitLab and Bitbucket have their own REST commit list APIs (<a href="https://docs.gitlab.com/ee/api/commits.html" target="_blank" rel="noopener noreferrer">GitLab repository commits</a>, <a href="https://developer.atlassian.com/cloud/bitbucket/rest/api-group-commits/" target="_blank" rel="noopener noreferrer">Bitbucket commits</a>); only the HTTP mapping would change.

## `/api/health` checks that Postgres answers

Compose treats the backend as healthy when `GET /api/health` returns 2xx, and the frontend waits on that. A handler that always returned `{"status": "ok"}` reported the process, not the catalogue. Queries would then 500 while Docker still considered the API ready. `wait_for_db()` only runs at boot, so a Postgres outage after startup stayed invisible.

The handler runs `SELECT 1` on the SQLAlchemy engine (the same probe as startup, without the 30-second retry). Failure is HTTP 503 `{"status": "unavailable"}`. `urllib.request.urlopen` in the existing Compose healthcheck already treats that as failure, so the check command did not change. On Postgres the probe sets a 2-second `statement_timeout`, under the healthcheck’s 5-second limit, so a stuck server fails the probe instead of hanging it.

GitHub is not part of readiness. Import needs it; listing repositories and contributors only needs the database.

## Schema is created on startup

SQLAlchemy <a href="https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.MetaData.create_all" target="_blank" rel="noopener noreferrer"><code>MetaData.create_all</code></a> runs when the API boots. That is enough for a compose-based demo. <a href="https://alembic.sqlalchemy.org/" target="_blank" rel="noopener noreferrer">Alembic</a> would be the production migration tool; it is not in this slice.

## Ports, without a full hexagonal tree

Import and contributor queries go through two interfaces in [`providers/base.py`](source/backend/app/providers/base.py): `VcsProvider` and `CatalogStore`. FastAPI routes call services; SQL lives in `SqlAlchemyCatalogStore`. ORM models stay as the entities.

That is the seam GitLab/Bitbucket need. A `domain/` / `adapters/` package split would not change behaviour here.

## Logs are structlog JSON on stdout

I log the import, not every request. Uvicorn already prints HTTP access lines. `ImportService` emits `sync.started` and `sync.finished` (owner, name, imported, skipped, status, duration_ms). `GitHubProvider` emits `github.response` on 404/409/403/429/other 4xx. I use <a href="https://www.structlog.org/en/stable/" target="_blank" rel="noopener noreferrer">structlog</a> so those events are JSON on stdout.

That is enough to debug a slow or partial import from `docker compose logs backend` without a log shipper. I did not add request IDs or a frontend logger.

## Prometheus exposition, not a Grafana stack

`GET /metrics` (proxied on port 8080) publishes a small set of series in the <a href="https://prometheus.io/docs/instrumenting/exposition_formats/" target="_blank" rel="noopener noreferrer">Prometheus text exposition format</a>: `catalog_sync_total{status}`, `catalog_sync_duration_seconds`, and `github_api_responses_total{status_code}`. Those are the numbers I would scrape for import success rate, duration, and GitHub 429s.

I did not add a Prometheus server, <a href="https://grafana.com/docs/grafana/latest/dashboards/" target="_blank" rel="noopener noreferrer">Grafana dashboards</a>, or a pre-built board. I know how to wire a <a href="https://prometheus.io/docs/prometheus/latest/configuration/configuration/" target="_blank" rel="noopener noreferrer">scrape job</a>, a Prometheus datasource, and RED-style panels on those series; they are the right follow-up once this service has traffic and an on-call viewer. For a single-user import demo they would add containers and credentials without changing behaviour, so I stopped at the exposition format.

## What I did not build, and what I would do next

I did not build these, on purpose:

- Authentication / multi-user isolation
- Celery/Redis (or any other job queue) and progress polling
- GitLab and Bitbucket clients (the interface is there; the HTTP mapping is not)
- Contributor identity merging
- Alembic migrations
- Retry/backoff against GitHub
- Caching, webhooks, or incremental `since=` imports (I always ask for the latest 1000)

With more time, in order: I would move import off the request thread; add Alembic; fetch only new SHAs using `since` / <a href="https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#use-conditional-requests-if-appropriate" target="_blank" rel="noopener noreferrer">conditional requests (ETags)</a>; implement a GitLab adapter against the same provider interface; pre-aggregate contributor counts if import size grows.
