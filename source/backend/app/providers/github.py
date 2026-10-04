from collections.abc import Iterator
from datetime import datetime, timezone

import httpx
import structlog

from app.metrics import observe_github_status
from app.providers.base import NormalizedCommit, ProviderError, RateLimited, RepositoryNotFound, VcsProvider

log = structlog.get_logger("app.github")


def _parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        if 'rel="next"' in part:
            start = part.find("<") + 1
            end = part.find(">")
            if start > 0 and end > start:
                return part[start:end]
    return None


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class GitHubProvider(VcsProvider):
    name = "github"

    def __init__(
        self,
        token: str = "",
        api_base: str = "https://api.github.com",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.transport = transport
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "circunomics-contributor-tracker",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._headers = headers

    def iter_recent_commits(
        self, owner: str, name: str, limit: int
    ) -> Iterator[list[NormalizedCommit]]:
        fetched = 0
        url: str | None = f"{self.api_base}/repos/{owner}/{name}/commits"
        params: dict[str, int] | None = {"per_page": 100}

        with httpx.Client(timeout=self.timeout, headers=self._headers, transport=self.transport) as client:
            while url and fetched < limit:
                response = client.get(url, params=params)
                params = None
                observe_github_status(response.status_code)
                if response.status_code == 404:
                    log.info("github.response", owner=owner, name=name, status_code=404)
                    raise RepositoryNotFound(f"GitHub repository {owner}/{name} was not found")
                if response.status_code == 409:
                    log.info("github.response", owner=owner, name=name, status_code=409)
                    return
                if response.status_code in (403, 429):
                    log.warning("github.response", owner=owner, name=name, status_code=response.status_code)
                    raise RateLimited(self._rate_limit_message(response))
                if response.status_code >= 400:
                    log.warning("github.response", owner=owner, name=name, status_code=response.status_code)
                    raise ProviderError(
                        f"GitHub API error {response.status_code}: {response.text[:300]}"
                    )

                remaining = limit - fetched
                page = [_map_commit(item) for item in response.json()[:remaining]]
                if not page:
                    return
                fetched += len(page)
                yield page
                url = _parse_next_link(response.headers.get("Link"))

    @staticmethod
    def _rate_limit_message(response: httpx.Response) -> str:
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        return (
            "GitHub rate-limited the import. Commits fetched so far were kept. "
            f"(remaining={remaining}, reset={reset})"
        )


def _map_commit(item: dict) -> NormalizedCommit:
    commit = item.get("commit") or {}
    author = commit.get("author") or {}
    name = author.get("name") or "unknown"
    email = author.get("email") or None
    date = author.get("date") or datetime.now(timezone.utc).isoformat()
    return NormalizedCommit(
        sha=item["sha"],
        author_name=name,
        author_email=email,
        committed_at=_parse_datetime(date),
        html_url=item.get("html_url") or "",
    )
