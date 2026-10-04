# Setup

The application runs entirely with Docker. You do not need Python, Node, or Postgres installed on the host.

You can drive Compose with **Make** (`make up`, …) or type the **Docker Compose** commands yourself. They are equivalent. Make is optional.

## Prerequisites

- Docker, with Compose v2 (`docker compose`)
- GNU Make, only if you prefer the `make` targets

`make help` lists every target.

## Environment file

Copy `.env.example` to `.env` if you do not already have one. A GitHub personal access token is optional but recommended (`GITHUB_TOKEN=ghp_...`). Without a token, GitHub allows 60 requests/hour, which is often too little to import 1000 commits.

```bash
make env
```

```bash
test -f .env || cp .env.example .env
```

`make env` will not overwrite an existing `.env`.

## Run

Build images and start Postgres, the API, and the Vue/nginx frontend:

```bash
make up
```

```bash
docker compose up --build
```

Detached:

```bash
make up-d
```

```bash
docker compose up --build -d
```

`make up` / `make up-d` also run the env-file step above if `.env` is missing.

Open [http://localhost:8080](http://localhost:8080).

The first import of a busy repository can take up to a couple of minutes (GitHub is paginated at 100 commits per request, up to 1000 commits). The UI stays on “Importing…” until that request finishes.

## Stop

Foreground: `Ctrl+C`. Then, or if you used detached mode:

```bash
make down
```

```bash
docker compose down
```

That keeps the `pgdata` volume. To drop the database as well:

```bash
make reset
```

```bash
docker compose down -v
```

## Logs

The API writes **structlog JSON** to stdout (import start/finish, GitHub 4xx on the provider). HTTP access lines still come from Uvicorn.

```bash
make logs
```

```bash
docker compose logs -f backend
```

Look for `"event": "sync.finished"` after an import or re-sync. Status is `success`, `partial`, or `failed`. Optional: set `LOG_LEVEL=DEBUG` in `.env` (Compose defaults to `INFO`).

## Metrics

With the stack running, Prometheus text is at [http://localhost:8080/metrics](http://localhost:8080/metrics) (nginx proxies `/metrics` to the backend):

```bash
make metrics
```

```bash
curl -sS http://localhost:8080/metrics
```

After an import you should see `catalog_sync_total`, `catalog_sync_duration_seconds`, and `github_api_responses_total`. There is no Prometheus or Grafana container in Compose; scrape the endpoint if you want a collector.

## Tests

Tests run inside Docker (SQLite in-memory, GitHub mocked). Coverage of `app/` is printed on every run:

```bash
make test
```

```bash
docker compose run --rm --no-deps --build backend pytest
```

HTML report (`htmlcov/index.html` inside the container):

```bash
make coverage
```

```bash
docker compose run --rm --no-deps --build backend pytest --cov-report=html
```

GitHub Actions uses `make test` (same Compose pytest invocation) on every push and pull request (`.github/workflows/tests.yml`).

## Database

```bash
make psql
```

```bash
docker compose exec db psql -U circunomics -d circunomics
```

## Layout

- `source/backend` — FastAPI, SQLAlchemy, provider adapters
- `source/frontend` — Vue 3 (built in the frontend image, served by nginx)
- nginx proxies `/api` and `/metrics` to the backend, so the browser only talks to port 8080
