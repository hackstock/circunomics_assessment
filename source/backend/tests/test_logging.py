import json
import logging

import httpx

from app.logging import configure_logging
from app.providers.base import ProviderError, RateLimited, RepositoryNotFound
from app.providers.github import GitHubProvider
from tests.fakes import FakeProvider, make_commit


def test_configure_logging_is_idempotent():
    configure_logging()
    configure_logging()


def _events(caplog):
    parsed = []
    for record in caplog.records:
        if not record.name.startswith("app."):
            continue
        try:
            parsed.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            continue
    return parsed


def _finished(caplog):
    return [event for event in _events(caplog) if event.get("event") == "sync.finished"]


def test_successful_import_logs_finished(client, provider: FakeProvider, caplog):
    caplog.set_level(logging.INFO)
    provider.pages = [[make_commit("aaa")]]
    response = client.post("/api/repositories", json={"full_name": "octo/hello"})
    assert response.status_code == 200
    finished = _finished(caplog)
    assert finished
    assert finished[-1]["status"] == "success"
    assert finished[-1]["imported"] == 1
    assert finished[-1]["owner"] == "octo"
    assert finished[-1]["name"] == "hello"
    assert "duration_ms" in finished[-1]


def test_partial_import_logs_partial_status(client, provider: FakeProvider, caplog):
    caplog.set_level(logging.INFO)
    provider.pages = [[make_commit("page1")], [make_commit("page2")]]
    provider.error_on_page = 1
    response = client.post("/api/repositories", json={"full_name": "octo/hello"})
    assert response.status_code == 200
    finished = _finished(caplog)
    assert finished[-1]["status"] == "partial"
    assert finished[-1]["imported"] == 1
    assert finished[-1]["error"]


def test_missing_github_repo_logs_deleted(client, provider: FakeProvider, caplog):
    caplog.set_level(logging.INFO)
    provider.fail_with = RepositoryNotFound("gone")
    response = client.post("/api/repositories", json={"full_name": "octo/missing"})
    assert response.status_code == 404
    finished = _finished(caplog)
    assert finished[-1]["status"] == "failed"
    assert finished[-1]["deleted"] is True


def test_github_error_statuses_are_logged(caplog):
    caplog.set_level(logging.INFO)
    cases = (
        (404, RepositoryNotFound, "info"),
        (429, RateLimited, "warning"),
        (500, ProviderError, "warning"),
    )
    for status, exc_type, level in cases:
        caplog.clear()

        def handler(_request, code=status):
            return httpx.Response(code)

        provider = GitHubProvider(
            api_base="https://example.test", transport=httpx.MockTransport(handler)
        )
        try:
            list(provider.iter_recent_commits("o", "r", 10))
        except exc_type:
            pass
        events = [event for event in _events(caplog) if event.get("event") == "github.response"]
        assert events, status
        assert events[-1]["status_code"] == status
        assert events[-1]["level"] == level


def test_github_empty_repo_409_is_logged(caplog):
    caplog.set_level(logging.INFO)
    provider = GitHubProvider(
        api_base="https://example.test",
        transport=httpx.MockTransport(lambda _r: httpx.Response(409)),
    )
    assert list(provider.iter_recent_commits("o", "empty", 10)) == []
    events = [event for event in _events(caplog) if event.get("event") == "github.response"]
    assert events[-1]["status_code"] == 409
    assert events[-1]["level"] == "info"
