import asyncio
from datetime import timezone

import httpx
import pytest

from app import db as dbmod
from app.config import settings
from app.db import get_db, wait_for_db
from app.main import app, lifespan
from app.providers.base import ProviderError, RateLimited
from app.providers.github import GitHubProvider, _map_commit, _parse_datetime, _parse_next_link
from app.providers.registry import get_provider


def test_parse_next_link_without_brackets():
    assert _parse_next_link('rel="next"') is None
    assert _parse_next_link('rel="last"') is None


def test_parse_naive_datetime():
    dt = _parse_datetime("2024-01-01T00:00:00")
    assert dt.tzinfo == timezone.utc


def test_map_commit_defaults_when_author_missing():
    mapped = _map_commit({"sha": "xyz"})
    assert mapped.author_name == "unknown"
    assert mapped.author_email is None
    assert mapped.html_url == ""


def test_github_empty_repository_409():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(409)

    provider = GitHubProvider(api_base="https://example.test", transport=httpx.MockTransport(handler))
    assert list(provider.iter_recent_commits("o", "empty", 10)) == []


def test_github_server_error_and_empty_page():
    calls = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, text="nope")
        return httpx.Response(200, json=[])

    provider = GitHubProvider(api_base="https://example.test", transport=httpx.MockTransport(handler))
    try:
        list(provider.iter_recent_commits("o", "r", 10))
        raised = False
    except ProviderError:
        raised = True
    assert raised

    provider = GitHubProvider(
        api_base="https://example.test",
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=[])),
    )
    assert list(provider.iter_recent_commits("o", "r", 10)) == []


def test_github_paginates_and_sends_token():
    seen = {"auth": None}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        if request.url.params.get("page") == "2":
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "bbb",
                        "html_url": "https://github.com/o/r/commit/bbb",
                        "commit": {"author": {"name": "B", "email": "b@e.com", "date": "2024-01-02T00:00:00Z"}},
                    }
                ],
            )
        return httpx.Response(
            200,
            headers={"Link": '<https://example.test/repos/o/r/commits?page=2>; rel="next"'},
            json=[
                {
                    "sha": "aaa",
                    "html_url": "https://github.com/o/r/commit/aaa",
                    "commit": {"author": {"name": "A", "email": "a@e.com", "date": "2024-01-01T00:00:00Z"}},
                }
            ],
        )

    provider = GitHubProvider(
        token="secret",
        api_base="https://example.test",
        transport=httpx.MockTransport(handler),
    )
    pages = list(provider.iter_recent_commits("o", "r", 10))
    assert [item.sha for page in pages for item in page] == ["aaa", "bbb"]
    assert seen["auth"] == "Bearer secret"


def test_wait_for_db_sqlite_and_get_db():
    if not settings.database_url.startswith("sqlite"):
        pytest.skip("compose injects Postgres; this covers the sqlite bootstrap path")
    wait_for_db()
    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass


def test_wait_for_db_succeeds_on_first_try(monkeypatch):
    class Ok:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(dbmod.engine, "connect", lambda: Ok())
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    dbmod.wait_for_db(attempts=30)


def test_wait_for_db_raises_when_unreachable(monkeypatch):
    class Boom:
        def __enter__(self):
            raise OSError("down")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dbmod.engine, "connect", lambda: Boom())
    monkeypatch.setattr(dbmod.time, "sleep", lambda _s: None)
    with pytest.raises(RuntimeError, match="Database was not ready"):
        dbmod.wait_for_db(attempts=2)


def test_get_db_closes_session(monkeypatch):
    closed = {"value": False}

    class FakeSession:
        def close(self):
            closed["value"] = True

    monkeypatch.setattr(dbmod, "SessionLocal", lambda: FakeSession())
    gen = dbmod.get_db()
    assert next(gen) is not None
    with pytest.raises(StopIteration):
        next(gen)
    assert closed["value"]


def test_lifespan_waits_and_creates_tables(monkeypatch):
    called = {"wait": False, "create": False}
    monkeypatch.setattr("app.main.wait_for_db", lambda: called.__setitem__("wait", True))
    monkeypatch.setattr(
        "app.main.Base.metadata.create_all",
        lambda bind: called.__setitem__("create", True),
    )

    async def run():
        async with lifespan(app):
            pass

    asyncio.run(run())
    assert called["wait"] and called["create"]


def test_get_provider_returns_github():
    assert get_provider().name == "github"


def test_github_forbidden_is_rate_limited():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1"},
        )

    provider = GitHubProvider(api_base="https://example.test", transport=httpx.MockTransport(handler))
    with pytest.raises(RateLimited) as exc:
        list(provider.iter_recent_commits("o", "r", 10))
    assert "remaining=0" in str(exc.value)


def test_github_respects_commit_limit():
    payload = [
        {
            "sha": sha,
            "html_url": f"https://github.com/o/r/commit/{sha}",
            "commit": {"author": {"name": "A", "email": "a@e.com", "date": "2024-01-01T00:00:00Z"}},
        }
        for sha in ("aaa", "bbb", "ccc")
    ]

    provider = GitHubProvider(
        api_base="https://example.test",
        transport=httpx.MockTransport(lambda _r: httpx.Response(200, json=payload)),
    )
    pages = list(provider.iter_recent_commits("o", "r", 2))
    assert [item.sha for page in pages for item in page] == ["aaa", "bbb"]
