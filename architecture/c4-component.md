# C4 Level 3 — Components

## Backend (FastAPI process)

HTTP enters `app.main:app` (lifespan: wait for DB, `create_all`). Routes live on `/api`; Prometheus is mounted on the app, not the API router.

Preview: PlantUML extension (`jebbs.plantuml`), cursor in the diagram, **PlantUML: Preview Current Diagram** (`Alt+D`).

```plantuml
@startuml contributor_tracker_backend
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/v2.0.1/C4_Component.puml

title Backend components — FastAPI / Uvicorn

Container_Boundary(backend, "backend container") {
    Component(main, "main.py", "FastAPI app", "CORS *, lifespan create_all, include_router /api, GET /metrics")
    Component(api, "api.py", "APIRouter", "health, repositories CRUD-ish, contributors, commits. Maps CatalogNotFound and RepositoryNotFound to 404, ValueError to 422")
    Component(imp, "ImportService", "Application service", "parse owner/repo, get_or_create, page upsert, partial/failed/success, structlog, Prometheus observe_sync")
    Component(qry, "QueryService", "Application service", "list/get repo, list contributors (sort/order/q/since/until/page), list commits by decoded identity")
    Component(store, "SqlAlchemyCatalogStore", "CatalogStore port", "SQL, ON CONFLICT DO NOTHING, contributor GROUP BY coalesce(email, name)")
    Component(gh, "GitHubProvider", "VcsProvider port", "httpx, per_page=100, Link next, 404/409/403/429/4xx, observe_github_status")
    Component(reg, "registry.get_provider", "Factory", "lru_cache GitHubProvider from settings")
    Component(idn, "identity.py", "Pure functions", "parse_full_name, contributor_identity, encode/decode contributor key")
    Component(obs, "logging.py + metrics.py", "Observability", "structlog JSON; catalog_sync_total, catalog_sync_duration_seconds, github_api_responses_total")
    Component(cfg, "config.Settings", "pydantic-settings", "database_url, github_token, github_api_base, commit_import_limit=1000, log_level")
    Component(dbm, "db.py + models.py", "SQLAlchemy 2", "engine, SessionLocal, Repository, Commit")
}

ContainerDb(postgres, "PostgreSQL", "circunomics")
System_Ext(github, "GitHub REST API")

Rel(main, api, "include_router prefix=/api")
Rel(main, obs, "configure_logging; prometheus_payload")
Rel(api, imp, "add_and_sync, sync_by_id")
Rel(api, qry, "list/get repositories, contributors, commits")
Rel(api, store, "Depends get_store")
Rel(api, reg, "Depends get_provider")
Rel(imp, store, "get_or_create, upsert_commits, persist, delete")
Rel(imp, gh, "iter_recent_commits via VcsProvider")
Rel(imp, idn, "parse_full_name")
Rel(imp, obs, "sync.started / sync.finished, observe_sync")
Rel(qry, store, "list_contributors, list_contributor_commits")
Rel(qry, idn, "encode/decode contributor_key")
Rel(gh, github, "GET commits")
Rel(gh, obs, "github.response, observe_github_status")
Rel(reg, gh, "constructs")
Rel(reg, cfg, "token, api_base")
Rel(store, dbm, "ORM")
Rel(dbm, postgres, "psycopg")
Rel(main, cfg, "settings at import")
@enduml
```

### HTTP surface

| Method | Path | Component |
| --- | --- | --- |
| GET | `/metrics` | `main.metrics` |
| GET | `/api/health` | `api.health` |
| GET | `/api/repositories` | `QueryService.list_repositories` |
| POST | `/api/repositories` | `ImportService.add_and_sync` |
| GET | `/api/repositories/{id}` | `QueryService.get_repository` |
| POST | `/api/repositories/{id}/sync` | `ImportService.sync_by_id` |
| GET | `/api/repositories/{id}/contributors` | `QueryService.list_contributors` |
| GET | `/api/repositories/{id}/contributors/{key}/commits` | `QueryService.list_commits` |

Pydantic schemas: `RepositoryCreate`, `RepositoryOut`, `SyncResult`, `ContributorPage`, `CommitPage` (`app/schemas.py`).

## Frontend (Vue 3 SPA)

Built with Vite, served as static files from nginx. Talks only to same-origin `/api`.

```plantuml
@startuml contributor_tracker_frontend
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/v2.0.1/C4_Component.puml

title Frontend components — Vue 3 + PrimeVue 4 Aura

Container_Boundary(spa, "nginx html/dist") {
    Component(app, "App.vue", "Shell", "Menubar, router-view")
    Component(router, "vue-router", "History mode", "/ , /repos/:id , /repos/:id/contributors/:contributorKey")
    Component(repos, "Repositories.vue", "Screen", "Import form, table, re-sync, partial as warning")
    Component(contrib, "Contributors.vue", "Screen", "Server-side search, since/until, sort, paginator")
    Component(detail, "ContributorDetail.vue", "Screen", "Paginated commits with GitHub html_url")
    Component(banner, "StatusBanner.vue", "Shared", "loading / error / warning / empty")
    Component(client, "api.js", "fetch wrapper", "JSON, FastAPI detail errors")
}

Rel(app, router, "router-view")
Rel(router, repos, "/")
Rel(router, contrib, "/repos/:id")
Rel(router, detail, "/repos/:id/contributors/:contributorKey")
Rel(repos, banner, "status")
Rel(contrib, banner, "status")
Rel(detail, banner, "status")
Rel(repos, client, "list/add/sync repositories")
Rel(contrib, client, "getRepository, listContributors")
Rel(detail, client, "listContributorCommits")
@enduml
```

PrimeVue widgets: Button, Card, DataTable, DatePicker, InputText, Message, Tag, Menubar, ProgressSpinner.
