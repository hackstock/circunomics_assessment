from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

sync_total = Counter(
    "catalog_sync_total",
    "Finished repository imports, labelled by last_sync_status.",
    ["status"],
)
sync_duration_seconds = Histogram(
    "catalog_sync_duration_seconds",
    "Wall time of a repository import.",
    buckets=(1, 5, 15, 30, 60, 120, 180, float("inf")),
)
github_api_responses_total = Counter(
    "github_api_responses_total",
    "GitHub HTTP responses from the commits API.",
    ["status_code"],
)


def observe_sync(status: str, duration_seconds: float) -> None:
    sync_total.labels(status=status).inc()
    sync_duration_seconds.observe(duration_seconds)


def observe_github_status(status_code: int) -> None:
    github_api_responses_total.labels(status_code=str(status_code)).inc()


def prometheus_payload() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
