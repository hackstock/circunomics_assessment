# C4 Level 2 — Containers

Compose services: `frontend` (nginx 1.27 + built Vue), `backend` (Uvicorn + FastAPI), `db` (Postgres 16). Only port **8080** is published. The backend is reached through nginx (`/api/`, `/metrics`). Volume `pgdata` holds the catalogue.

Preview: PlantUML extension (`jebbs.plantuml`), cursor in the diagram, **PlantUML: Preview Current Diagram** (`Alt+D`).

```plantuml
@startuml contributor_tracker_containers
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/v2.0.1/C4_Container.puml

title Contributor tracker — containers (docker compose)

Person(user, "Reviewer / operator", "Browser on localhost:8080")

System_Boundary(compose, "docker compose") {
    Container(frontend, "frontend", "nginx 1.27-alpine + Vue 3 SPA", "Serves PrimeVue UI. Proxies /api (read timeout 180s) and /metrics. SPA fallback try_files")
    Container(backend, "backend", "Python 3.12, Uvicorn, FastAPI", "Sync def routes in a thread pool. Import, queries, structlog JSON, GET /metrics. Health: GET /api/health")
    ContainerDb(db, "db", "PostgreSQL 16 Alpine", "repositories and commits. Unique (provider, owner, name) and (repository_id, sha). Volume pgdata")
}

System_Ext(github, "GitHub REST API", "api.github.com")
System_Ext(registry, "Image registries", "python:3.12-slim, node:22-alpine (build), nginx, postgres")

Rel(user, frontend, "HTML, JS, XHR", "HTTP :8080")
Rel(frontend, backend, "GET/POST /api/*, GET /metrics", "HTTP backend:8000")
Rel(backend, db, "SQLAlchemy 2 + psycopg", "postgresql+psycopg://...@db:5432/circunomics")
Rel(backend, github, "List commits", "HTTPS, GITHUB_TOKEN optional")
Rel(registry, frontend, "Base images at build")
Rel(registry, backend, "Base image at build")
Rel(registry, db, "postgres:16-alpine")
@enduml
```

## Compose wiring

| Container | Image / build | Env | Health |
| --- | --- | --- | --- |
| `db` | `postgres:16-alpine` | `POSTGRES_USER/PASSWORD/DB=circunomics` | `pg_isready` |
| `backend` | `./source/backend` | `DATABASE_URL`, `GITHUB_TOKEN`, `GITHUB_API_BASE`, `LOG_LEVEL` | `GET http://127.0.0.1:8000/api/health` after db is healthy |
| `frontend` | `./source/frontend` (Node build, nginx runtime) | — | starts after backend is healthy; publishes `8080:80` |

## nginx locations (`source/frontend/nginx.conf`)

| Path | Behaviour |
| --- | --- |
| `/metrics` | `proxy_pass http://backend:8000/metrics` |
| `/api/` | `proxy_pass http://backend:8000/api/` , `proxy_read_timeout 180s` |
| `/` | static `dist/` + `try_files` for Vue Router history mode |

## Not a container

Makefile targets wrap Compose (`up`, `test`, `logs`, `metrics`, `psql`). GitHub Actions runs `make test` (`docker compose run --rm --no-deps --build backend pytest`) with SQLite in-memory, not this Postgres.
