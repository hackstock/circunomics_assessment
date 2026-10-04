# C4 Level 1 — System context

The contributor tracker is a single Compose application. The only required external system is GitHub. A token is optional; without it the REST primary limit is 60 requests/hour.

Preview: PlantUML extension (`jebbs.plantuml`), cursor in the diagram, **PlantUML: Preview Current Diagram** (`Alt+D`).

```plantuml
@startuml contributor_tracker_context
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/v2.0.1/C4_Context.puml

title Contributor tracker — system context

Person(user, "Reviewer / operator", "Imports owner/repo names and browses contributors in a browser")
Person(ci, "GitHub Actions", "Runs make test on push and pull_request")

System(tracker, "Contributor tracker", "Imports up to 1000 recent commits per GitHub repository and serves contributor queries")

System_Ext(github, "GitHub REST API", "GET /repos/{owner}/{name}/commits, pagination Link headers, 404 / 409 / 403 / 429")
System_Ext(scraper, "Optional Prometheus scraper", "Not in Compose. May scrape GET /metrics later")

Rel(user, tracker, "Uses UI, API, metrics", "HTTPS localhost:8080")
Rel(tracker, github, "List commits (per_page=100, up to 10 pages)", "HTTPS JSON, optional Bearer token")
Rel(ci, tracker, "Builds backend image, pytest", "docker compose run")
Rel(scraper, tracker, "Scrapes catalog_sync_* and github_api_responses_total", "GET /metrics")
@enduml
```

## Boundary notes

- **In:** Vue SPA, nginx, FastAPI/Uvicorn, PostgreSQL 16, structlog stdout, Prometheus *exposition* (`/metrics`).
- **Out of this system:** GitLab/Bitbucket clients, Alembic, Celery/Redis, Grafana, authentication.
