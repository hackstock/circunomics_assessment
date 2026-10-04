# C4 Level 4 — Code, data, and runtime flows

C4 “code” is the tables, the import state machine, and how a browser request reaches SQL or GitHub.

## Data model

```mermaid
erDiagram
    repositories ||--o{ commits : has
    repositories {
        int id PK
        string provider UK "github"
        string owner UK
        string name UK
        timestamptz last_sync_attempted_at
        timestamptz last_sync_succeeded_at
        string last_sync_status "success / partial / failed"
        text last_sync_error
    }
    commits {
        int id PK
        int repository_id FK,UK
        string sha UK
        string author_name
        string author_email "nullable"
        timestamptz committed_at
        string html_url
        timestamptz created_at
    }
```

Contributor identity is **not** a table. Queries group by `coalesce(nullif(lower(author_email), ''), lower(author_name))`. The UI passes that key as url-safe base64 (`identity.encode_contributor_key`).

## Import state machine

```mermaid
stateDiagram-v2
    [*] --> Attempted: persist last_sync_attempted_at
    Attempted --> Pages: iter_recent_commits
    Pages --> Pages: upsert page, commit
    Pages --> Success: all pages, persist succeeded_at
    Pages --> Partial: RateLimited or ProviderError after some rows
    Pages --> FailedEmpty: RepositoryNotFound and commit_count = 0
    Pages --> FailedKeep: RepositoryNotFound and commits exist
    Pages --> FailedProvider: ProviderError with nothing imported
    Success --> [*]
    Partial --> [*]: HTTP 200 + message
    FailedEmpty --> [*]: delete row, HTTP 404
    FailedKeep --> [*]: HTTP 404, row kept
    FailedProvider --> [*]: HTTP 200 + message
```

Each page is committed before the next GitHub GET. Re-import uses `ON CONFLICT DO NOTHING` on `(repository_id, sha)`.

## Request paths

```mermaid
sequenceDiagram
    actor User
    participant Nginx as nginx :8080
    participant API as FastAPI thread pool
    participant Imp as ImportService
    participant GH as GitHubProvider
    participant Store as CatalogStore
    participant PG as PostgreSQL

    User->>Nginx: POST /api/repositories {full_name}
    Nginx->>API: proxy_read_timeout 180s
    API->>Imp: add_and_sync
    Imp->>Store: get_or_create_repository
    Store->>PG: INSERT repositories if needed
    loop up to 10 pages
        Imp->>GH: iter_recent_commits
        GH->>GH: GET .../commits?per_page=100
        GH-->>Imp: NormalizedCommit[]
        Imp->>Store: upsert_commits ON CONFLICT DO NOTHING
        Store->>PG: COMMIT
    end
    Imp-->>API: SyncResult
    API-->>User: 200 or 404/422

    User->>Nginx: GET /api/repositories/{id}/contributors
    Nginx->>API: QueryService
    API->>Store: GROUP BY identity, filter, sort, page
    Store->>PG: SELECT
    PG-->>User: ContributorPage
```

## Observability (same process, not extra containers)

| Signal | Where | Shape |
| --- | --- | --- |
| Logs | stdout | structlog JSON: `sync.started`, `sync.finished`, `github.response` |
| Metrics | `GET /metrics` | `catalog_sync_total{status}`, `catalog_sync_duration_seconds`, `github_api_responses_total{status_code}` |
| HTTP access | Uvicorn | default access log |
| Health | `GET /api/health` | `{status: ok}` after `SELECT 1`; 503 `{status: unavailable}` when Postgres does not answer |

## Test runtime (not the Compose graph)

Pytest uses SQLite in-memory, a no-op FastAPI lifespan, and `FakeProvider`. That is why `make test` uses `--no-deps` and does not start Postgres or nginx.

## Deliberately absent from every diagram

GitLab/Bitbucket adapters, Alembic, Celery/Redis, Grafana, Prometheus server, authentication, job progress polling.
