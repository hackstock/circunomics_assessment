from app.providers.base import RateLimited, RepositoryNotFound
from app.providers.github import GitHubProvider, _map_commit, _parse_next_link
import httpx


def test_parse_next_link():
    header = (
        '<https://api.github.com/repos/o/r/commits?page=2>; rel="next", '
        '<https://api.github.com/repos/o/r/commits?page=5>; rel="last"'
    )
    assert _parse_next_link(header).endswith("page=2")
    assert _parse_next_link(None) is None


def test_map_commit_uses_git_author_fields():
    mapped = _map_commit(
        {
            "sha": "abc",
            "html_url": "https://github.com/o/r/commit/abc",
            "commit": {
                "author": {
                    "name": "Ada",
                    "email": "ada@example.com",
                    "date": "2024-01-01T00:00:00Z",
                }
            },
        }
    )
    assert mapped.sha == "abc"
    assert mapped.author_name == "Ada"
    assert mapped.author_email == "ada@example.com"
    assert mapped.committed_at.year == 2024


def test_github_rate_limit_raises():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"X-RateLimit-Remaining": "0"})

    provider = GitHubProvider(api_base="https://example.test", transport=httpx.MockTransport(handler))
    try:
        list(provider.iter_recent_commits("o", "r", 10))
        raised = False
    except RateLimited:
        raised = True
    assert raised


def test_github_missing_repo_raises():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    provider = GitHubProvider(api_base="https://example.test", transport=httpx.MockTransport(handler))
    try:
        list(provider.iter_recent_commits("o", "missing", 10))
        raised = False
    except RepositoryNotFound:
        raised = True
    assert raised
